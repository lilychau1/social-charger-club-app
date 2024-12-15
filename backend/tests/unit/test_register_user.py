import json
import pytest
from unittest.mock import patch, MagicMock
from register_user.app import lambda_handler

@pytest.fixture()
def apigw_event():
    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "username": "testuser",
            "user_type": "consumer"
        })
    }

@patch('register_user.app.table')
def test_lambda_handler_success(mock_table, apigw_event):
    mock_table.put_item.return_value = {}

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'user_id' in body
    assert 'consumer_id' in body
    assert 'producer_id' in body
    assert body['message'].startswith("User data for")

@patch('register_user.app.table')
def test_lambda_handler_error(mock_table, apigw_event):
    mock_table.put_item.side_effect = Exception("DynamoDB error")

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body
