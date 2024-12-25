import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from register_user.app import lambda_handler

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Load environment variables from the env-vars.json file
def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['USER_POOL_ID'] = env_vars['RegisterUserFunction']['USER_POOL_ID']
        os.environ['USER_POOL_CLIENT_ID'] = env_vars['RegisterUserFunction']['USER_POOL_CLIENT_ID']
        os.environ['USER_TABLE_NAME'] = env_vars['RegisterUserFunction']['USER_TABLE_NAME']

# Call this function before your tests (to ensure environment variables are set)
load_env_vars()
table_name = os.environ['USER_TABLE_NAME']

@pytest.fixture(scope='module')
def test_user():
    return {
        'email': 'testuser@example.com',
        'password': 'TestPassword123!',
        'username': 'testuser',
        'userType': 'consumer'
    }

@pytest.fixture(scope='module')
def duplicate_user():
    return {
        'email': 'duplicateuser@example.com',
        'password': 'DuplicatePassword123!',
        'username': 'duplicateuser',
        'userType': 'consumer'
    }

# Cleanup functions
def clean_up_cognito_user(email):
    try:
        cognito.admin_delete_user(
            UserPoolId=os.environ['USER_POOL_ID'],
            Username=email
        )
    except ClientError as e:
        print(f"Error cleaning up Cognito user: {str(e)}")

def clean_up_dynamodb_user(user_id):
    table = dynamodb.Table(table_name)
    try:
        table.delete_item(
            Key={'userId': user_id}
        )
    except ClientError as e:
        print(f"Error cleaning up DynamoDB user: {str(e)}")

# Integration tests
def test_lambda_handler_integration(test_user):
    # Clean up any existing test user in Cognito user pool
    clean_up_cognito_user(test_user['email'])

    event = {
        'httpMethod': 'POST',
        'body': json.dumps(test_user)
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'userId' in body.keys()
    assert 'consumerId' in body.keys()
    assert body['message'].startswith("User data for")

    user_id = body['userId']

    # Verify user in Cognito
    try:
        cognito_user = cognito.admin_get_user(
            UserPoolId=os.environ['USER_POOL_ID'],
            Username=test_user['email']
        )
        assert cognito_user['Username'] == test_user['email']
    except ClientError as e:
        pytest.fail(f"User not found in Cognito: {str(e)}")

    # Verify user in DynamoDB
    table = dynamodb.Table(table_name)
    try:
        # Email is used as GSI with index name of 'EmailIndex'
        response = table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(test_user['email'])
        )

        # Check if the inserted item was found in the response
        db_user = response['Items'][0] if response['Items'] else None
        assert db_user['username'] == test_user['username']
        assert db_user['userType'] == test_user['userType']
    except ClientError as e:
        pytest.fail(f"User not found in DynamoDB: {str(e)}")

    # Clean up cognito and dynamodb by deleting the user/record created for the test
    clean_up_cognito_user(test_user['email'])
    clean_up_dynamodb_user(user_id)

def test_lambda_handler_duplicate_user(duplicate_user):
    clean_up_cognito_user(duplicate_user['email'])

    event = {
        'httpMethod': 'POST',
        'body': json.dumps(duplicate_user)
    }

    # Create the first user
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    user_id = body['userId']

    # Try to create the same user again
    duplicate_response = lambda_handler(event, None)
    
    assert duplicate_response['statusCode'] == 400
    duplicate_body = json.loads(duplicate_response['body'])
    assert 'error' in duplicate_body
    assert 'UsernameExistsException' in duplicate_body['error']

    # Clean up cognito and dynamodb by deleting the user/record created for the test
    clean_up_cognito_user(duplicate_user['email'])
    clean_up_dynamodb_user(user_id)

def test_lambda_handler_invalid_request():
    # Test invalid email format
    invalid_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'email': 'invalidemail',
            'password': 'Invalid123!',
            'username': 'invaliduser',
            'userType': 'consumer'
        })
    }

    response = lambda_handler(invalid_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'InvalidParameterException' in body['error']

def test_lambda_handler_missing_fields():
    missing_field_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'password': 'Password123!',
            'username': 'missingemailuser',
            'userType': 'consumer'
        })
    }

    response = lambda_handler(missing_field_event, None)
    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Username' in body['error']

# Run the tests
if __name__ == '__main__':
    pytest.main([__file__])
