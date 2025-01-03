import os
import boto3
import json
import pytest
from unittest.mock import patch
from request_match.app import lambda_handler

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['MATCH_REQUESTS_TABLE_NAME'] = env_vars['RequestMatchFunction']['MATCH_REQUESTS_TABLE_NAME']
        os.environ['USERS_TABLE_NAME'] = env_vars['RequestMatchFunction']['USERS_TABLE_NAME']
        os.environ['PARAMETER_PREFIX'] = env_vars['RequestMatchFunction']['PARAMETER_PREFIX']
        os.environ['TEST_RECIPIENT_EMAIL'] = env_vars['RequestMatchFunction']['TEST_RECIPIENT_EMAIL']
        os.environ['TEST_SES_EMAIL'] = env_vars['RequestMatchFunction']['TEST_SES_EMAIL']

load_env_vars()

mock_recipient_email = os.environ.get('TEST_RECIPIENT_EMAIL')
mock_recipient_consumer_id = 'mock-recipient-consumer-id'

@pytest.fixture(scope='module')
def dynamodb_table_users():
    table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME'))
    
    test_data = {
        'userId': 'mock-user-id',
        'consumerId': mock_recipient_consumer_id,
        'email': mock_recipient_email
    }
    
    table.put_item(Item=test_data)
    yield table
    table.delete_item(Key={'userId': test_data['userId']})

mock_request_id = 'mock-request-id'
mock_request_id_2 = 'mock-request-id-2'
mock_request_id_3 = 'mock-request-id-3'

@pytest.fixture(scope='module')
def dynamodb_table_match_requests():
    table = dynamodb.Table(os.environ.get('MATCH_REQUESTS_TABLE_NAME'))
    
    yield table
    table.delete_item(Key={'requestId': mock_request_id})
    table.delete_item(Key={'requestId': mock_request_id_2})

@pytest.fixture(scope='module')
def mock_ses_client():
    ses_client = boto3.client('ses')
    yield ses_client

@patch('request_match.app.uuid')
def test_lambda_handler(mock_uuid, dynamodb_table_users, dynamodb_table_match_requests, mock_ses_client):
    mock_uuid.uuid4.return_value = mock_request_id

    mock_sender_consumer_id = 'mock-sender-consumer-id'

    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'senderConsumerId': mock_sender_consumer_id,
            'recipientConsumerId': mock_recipient_consumer_id,
            'meetingStartTime': '2025-01-01T10:00:00Z',
            'meetingEndTime': '2025-01-01T11:00:00Z',
            'matchEventType': 'Business',
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Match request sent successfully'

    response = dynamodb_table_match_requests.scan()
    items = [item for item in response['Items'] if item['requestId'] == mock_request_id]
    
    assert len(items) == 1
    assert items[0]['senderConsumerId'] == mock_sender_consumer_id
    assert items[0]['recipientConsumerId'] == mock_recipient_consumer_id
    assert items[0]['matchStatus'] == 'Pending'
    
    sent_emails = mock_ses_client.list_verified_email_addresses()['VerifiedEmailAddresses']
    assert mock_recipient_email in sent_emails


@patch('request_match.app.uuid')
def test_lambda_handler_missing_fields_error(mock_uuid, dynamodb_table_users, dynamodb_table_match_requests, mock_ses_client):
    mock_uuid.uuid4.return_value = mock_request_id_2

    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'senderConsumerId': 'mock-sender-consumer-id',
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == 'Missing required fields in request body'

    response = dynamodb_table_match_requests.scan()
    items = [item for item in response['Items'] if item['requestId'] == mock_request_id_2]

    assert len(items) == 0


@patch('request_match.app.uuid')
def test_lambda_handler_user_not_found_error(mock_uuid, dynamodb_table_users, dynamodb_table_match_requests, mock_ses_client):
    mock_uuid.uuid4.return_value = mock_request_id_3

    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'senderConsumerId': 'mock-sender-consumer-id',
            'recipientConsumerId': 'non-existent-consumer-id',
            'meetingStartTime': '2025-01-01T10:00:00Z',
            'meetingEndTime': '2025-01-01T11:00:00Z',
            'matchEventType': 'Business',
        }),
    }
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error'] == 'Recipient user not found'

    response = dynamodb_table_match_requests.scan()

    items = [item for item in response['Items'] if item['requestId'] == mock_request_id_3]
    assert len(items) == 1
