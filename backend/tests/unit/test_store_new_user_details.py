import json
import pytest
import os
from botocore.exceptions import ClientError
from unittest.mock import patch

from store_new_user_details.app import lambda_handler  # Correct import path

@pytest.fixture()
def apigw_event():
    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "userId": "user123",
            "consumerId": "consumer123",
            "producerId": "producer123",
            "updates": {
                "basic": {"name": "John Doe", "email": "john@example.com"},
                "consumer": {"preference": "vegetarian"},
                "producer": {"specialty": "organic"}
            }
        })
    }

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'USERS_TABLE_NAME': 'UsersTable',
        'CONSUMERS_TABLE_NAME': 'ConsumersTable',
        'PRODUCERS_TABLE_NAME': 'ProducersTable'
    }):
        yield

@patch('store_new_user_details.app.dynamodb')
def test_lambda_handler_success(mock_dynamodb, apigw_event):
    mock_dynamodb.update_item.return_value = {}

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "User details updated successfully"

@patch('store_new_user_details.app.dynamodb')
def test_lambda_handler_dynamodb_error(mock_dynamodb, apigw_event):
    mock_dynamodb.update_item.side_effect = ClientError(
        {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'The conditional request failed'}},
        'UpdateItem'
    )

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Client error' in body['error']

@patch('store_new_user_details.app.dynamodb')
def test_lambda_handler_general_error(mock_dynamodb, apigw_event):
    mock_dynamodb.update_item.side_effect = Exception("Unexpected error")

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Server error' in body['error']

def test_lambda_handler_options():
    options_event = {"httpMethod": "OPTIONS"}
    response = lambda_handler(options_event, "")

    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']

@patch('store_new_user_details.app.dynamodb')
def test_lambda_handler_partial_update(mock_dynamodb, apigw_event):
    apigw_event['body'] = json.dumps({
        "userId": "user123",
        "consumerId": "consumer123",
        "updates": {
            "basic": {"name": "Jane Doe"},
            "consumer": {"preference": "vegan"}
        }
    })
    
    mock_dynamodb.update_item.return_value = {}

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "User details updated successfully"
