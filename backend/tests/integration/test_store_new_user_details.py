import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from store_new_user_details.app import lambda_handler

# Initialize DynamoDB client and resource
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')

# Load environment variables from a configuration file (e.g., `env.json`)
def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['USERS_TABLE_NAME'] = env_vars['StoreUserDetailsFunction']['USERS_TABLE_NAME']
        os.environ['CONSUMERS_TABLE_NAME'] = env_vars['StoreUserDetailsFunction']['CONSUMERS_TABLE_NAME']
        os.environ['PRODUCERS_TABLE_NAME'] = env_vars['StoreUserDetailsFunction']['PRODUCERS_TABLE_NAME']

# Load environment variables before running tests
load_env_vars()

@pytest.fixture(scope='module')
def test_user_updates():
    return {
        "userId": f"testuser_{os.urandom(4).hex()}",
        "consumerId": f"testconsumer_{os.urandom(4).hex()}",
        "producerId": f"testproducer_{os.urandom(4).hex()}",
        "updates": {
            "basic": {"name": "John Doe", "email": f"johndoe_{os.urandom(4).hex()}@example.com"},
            "consumer": {"preference": "vegetarian"},
            "producer": {"specialty": "organic"}
        }
    }

# Cleanup functions
def clean_up_dynamodb_user(table_name, key_name, key_value):
    table = dynamodb.Table(table_name)
    try:
        table.delete_item(Key={key_name: key_value})
    except ClientError as e:
        print(f"Error cleaning up DynamoDB record in {table_name}: {str(e)}")

# Integration Tests
def test_lambda_handler_integration(test_user_updates):
    event = {
        "httpMethod": "POST",
        "body": json.dumps(test_user_updates)
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "User details updated successfully"

    # Verify updates in Users table
    users_table = dynamodb.Table(os.environ['USERS_TABLE_NAME'])
    user_data = users_table.get_item(Key={"userId": test_user_updates["userId"]}).get("Item")
    assert user_data is not None
    assert user_data.get("name") == test_user_updates["updates"]["basic"]["name"]
    assert user_data.get("email") == test_user_updates["updates"]["basic"]["email"]

    # Verify updates in Consumers table
    consumers_table = dynamodb.Table(os.environ['CONSUMERS_TABLE_NAME'])
    consumer_data = consumers_table.get_item(Key={"consumerId": test_user_updates["consumerId"]}).get("Item")
    assert consumer_data is not None
    assert consumer_data.get("preference") == test_user_updates["updates"]["consumer"]["preference"]

    # Verify updates in Producers table
    producers_table = dynamodb.Table(os.environ['PRODUCERS_TABLE_NAME'])
    producer_data = producers_table.get_item(Key={"producerId": test_user_updates["producerId"]}).get("Item")
    assert producer_data is not None
    assert producer_data.get("specialty") == test_user_updates["updates"]["producer"]["specialty"]

    # Clean up after test
    clean_up_dynamodb_user(os.environ['USERS_TABLE_NAME'], "userId", test_user_updates["userId"])
    clean_up_dynamodb_user(os.environ['CONSUMERS_TABLE_NAME'], "consumerId", test_user_updates["consumerId"])
    clean_up_dynamodb_user(os.environ['PRODUCERS_TABLE_NAME'], "producerId", test_user_updates["producerId"])

def test_lambda_handler_invalid_request():
    invalid_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "userId": "",
            "updates": {}
        })
    }

    response = lambda_handler(invalid_event, None)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert body['error'] == "Invalid input. userId and updates are required."

def test_lambda_handler_options():
    options_event = {"httpMethod": "OPTIONS"}
    
    response = lambda_handler(options_event, None)
    
    assert response['statusCode'] == 200