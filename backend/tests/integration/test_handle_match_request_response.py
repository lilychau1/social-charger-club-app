import os
import boto3
import json
import pytest
from unittest.mock import patch
from handle_match_request_response.app import lambda_handler

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['MATCH_REQUESTS_TABLE_NAME'] = env_vars['HandleMatchRequestResponseFunction']['MATCH_REQUESTS_TABLE_NAME']
        os.environ['USERS_TABLE_NAME'] = env_vars['HandleMatchRequestResponseFunction']['USERS_TABLE_NAME']
        os.environ['PARAMETER_PREFIX'] = env_vars['HandleMatchRequestResponseFunction']['PARAMETER_PREFIX']
        os.environ['TEST_SENDER_EMAIL'] = env_vars['HandleMatchRequestResponseFunction']['TEST_SENDER_EMAIL']
        os.environ['TEST_SES_EMAIL'] = env_vars['HandleMatchRequestResponseFunction']['TEST_SES_EMAIL']

load_env_vars()

mock_sender_email = os.environ.get('TEST_SENDER_EMAIL')
mock_sender_consumer_id = 'mock-sender-consumer-id'
mock_recipient_consumer_id = 'mock-recipient-consumer-id'
mock_request_id = 'mock-request-id'
match_status_original_value = 'original_value'

@pytest.fixture(scope='module')
def dynamodb_table_users():
    table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME'))
    test_data = {
        'userId': 'mock-user-id',
        'consumerId': mock_sender_consumer_id,
        'email': mock_sender_email
    }
    table.put_item(Item=test_data)
    yield table
    table.delete_item(Key={'userId': test_data['userId']})

def revert_match_status_to_original_value(table):
    table.update_item(
        Key={'requestId': mock_request_id},
        UpdateExpression="SET matchStatus = :original_value",
        ExpressionAttributeValues={':original_value': match_status_original_value}
    )
    
@pytest.fixture(scope='module')
def dynamodb_table_match_requests():
    table = dynamodb.Table(os.environ.get('MATCH_REQUESTS_TABLE_NAME'))
    test_data = {
        'requestId': mock_request_id,
        'senderConsumerId': mock_sender_consumer_id,
        'recipientConsumerId': mock_recipient_consumer_id, 
        'matchStatus': 'original-value'
    }
    table.put_item(Item=test_data)
    yield table
    table.delete_item(Key={'requestId': test_data['requestId']})

@pytest.fixture(scope='module')
def mock_ses_client():
    ses_client = boto3.client('ses')
    yield ses_client

def test_lambda_handler_success(
    dynamodb_table_users, 
    dynamodb_table_match_requests, 
    mock_ses_client
):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'requestId': mock_request_id,
            'senderConsumerId': mock_sender_consumer_id,
            'recipientConsumerId': mock_recipient_consumer_id,
            'requestResponse': 'Accept'
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Match request response sent successfully'

    response = dynamodb_table_match_requests.scan()
    items = [item for item in response['Items'] if item['requestId'] == mock_request_id]
    assert items[0]['matchStatus'] == 'Accepted'

    sent_emails = mock_ses_client.list_verified_email_addresses()['VerifiedEmailAddresses']
    assert mock_sender_email in sent_emails
    
    revert_match_status_to_original_value(dynamodb_table_match_requests)
    
def test_lambda_handler_missing_fields_error(
    dynamodb_table_users, 
    dynamodb_table_match_requests
):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            # Missing 'requestId', 'recipientConsumerId', and 'requestResponse'
            'senderConsumerId': mock_sender_consumer_id,
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == 'Missing required fields in request body'

    response = dynamodb_table_match_requests.scan()
    items = [item for item in response['Items'] if item['requestId'] == mock_request_id]
    # Ensure the match request status has not changed due to the missing fields
    assert items[0]['matchStatus'] == match_status_original_value
    
    revert_match_status_to_original_value(dynamodb_table_match_requests)

def test_lambda_handler_recipient_not_found_email_error(
    dynamodb_table_match_requests,
    dynamodb_table_users
):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'requestId': mock_request_id,
            'senderConsumerId': mock_sender_consumer_id,
            'recipientConsumerId': 'non-existent-recipient-consumer-id',  # Invalid recipient ID
            'requestResponse': 'Accept'
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 200

    response = dynamodb_table_match_requests.scan()
    items = [item for item in response['Items'] if item['requestId'] == mock_request_id]

    assert items[0]['matchStatus'] == 'Accepted'

    revert_match_status_to_original_value(dynamodb_table_match_requests)
