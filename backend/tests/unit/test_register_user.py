import json
import pytest
import os
from botocore.exceptions import ClientError
from unittest.mock import patch, MagicMock
from register_user.app import lambda_handler

@pytest.fixture()
def apigw_event():
    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "username": "testuser",
            "userType": "consumer"
        })
    }

@patch('register_user.app.table')
@patch('register_user.app.cognito')
@patch('register_user.app.generate_ids')
def test_lambda_handler_success(mock_generate_id, mock_cognito, mock_table, apigw_event):
    mock_generate_id.return_value = {'userId', 'consumerId', 'producerId'}
    mock_cognito.sign_up.return_value = {}
    mock_table.put_item.return_value = {}

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'userId' in body
    assert 'consumerId' in body
    assert 'producerId' in body
    assert body['message'].startswith("User data for")

@patch('register_user.app.cognito')
def test_lambda_handler_cognito_error(mock_cognito, apigw_event):
    error_response = {'Error': {'Code': 'UsernameExistsException', 'Message': 'User already exists'}}
    mock_cognito.sign_up.side_effect = ClientError(error_response, 'sign_up')

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'User already exists' in body['error']
 
@patch('register_user.app.cognito')
@patch('register_user.app.table')
def test_lambda_handler_dynamodb_error(mock_table, mock_cognito, apigw_event):
    mock_cognito.sign_up.return_value = {}
    mock_table.put_item.side_effect = Exception("DynamoDB error")

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body

def test_lambda_handler_options(apigw_event):
    apigw_event['httpMethod'] = 'OPTIONS'
    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']