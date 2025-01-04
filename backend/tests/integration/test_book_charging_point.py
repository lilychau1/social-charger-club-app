import json
import pytest
from unittest.mock import MagicMock, patch
import os
import boto3
from botocore.exceptions import ClientError
from lambda_functions.book_charging_point.app import lambda_handler, book_charging_point

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['BookChargingPointFunction']['CHARGING_POINTS_TABLE_NAME']
        os.environ['BOOKINGS_TABLE_NAME'] = env_vars['BookChargingPointFunction']['BOOKINGS_TABLE_NAME']
        os.environ['PARAMETER_PREFIX'] = env_vars['BookChargingPointFunction']['PARAMETER_PREFIX']
        os.environ['SECRET_NAME'] = env_vars['BookChargingPointFunction']['SECRET_NAME']

load_env_vars()

@pytest.fixture(scope='module')
def dynamodb_table_charging_points():
    table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME'))
    
    test_data = {
        'oocpChargePointId': 'test-point-id',
        'isAvailable': True,
        'statusUpdatedAt': '2024-12-30T00:00:00',
        'currentBookedConsumerId': None
    }
    
    table.put_item(Item=test_data)

    yield table
    
    table.delete_item(Key={'oocpChargePointId': test_data['oocpChargePointId']})

@pytest.fixture(scope='module')
def dynamodb_table_bookings():
    table = dynamodb.Table(os.environ['BOOKINGS_TABLE_NAME'])

    yield table
    
    # Clean up test data (can expand this if necessary)
    pass

@pytest.fixture
def mock_requests():
    with patch('lambda_functions.book_charging_point.app.requests') as mock_requests:
        yield mock_requests

@pytest.fixture
def mock_ssm_and_secrets():
    with patch('lambda_functions.book_charging_point.app.get_ssm_parameter') as mock_ssm, \
         patch('lambda_functions.book_charging_point.app.get_secret_value') as mock_secrets:
        mock_ssm.return_value = 'mock-ssm-value'
        mock_secrets.return_value = 'mock-secret-value'
        yield mock_ssm, mock_secrets

def test_book_charging_point_success(mock_requests, mock_ssm_and_secrets):
    mock_ssm, mock_secrets = mock_ssm_and_secrets

    mock_requests.post.return_value.status_code = 200
    mock_requests.post.return_value.json.return_value = {"message": "Booking confirmed"}

    response = book_charging_point(
        system="Virta",
        oocp_charge_point_id="test-point-id",
        connector_id="1",
        start_time="2024-12-30T12:00:00",
        end_time="2024-12-30T13:00:00"
    )

    assert response['status'] == 'success'
    mock_requests.post.assert_called_once()

@patch('lambda_functions.book_charging_point.app.uuid')
def test_lambda_handler_success(mock_uuid, dynamodb_table_charging_points, dynamodb_table_bookings, mock_requests, mock_ssm_and_secrets):
    mock_uuid.uuid4.return_value = 'mock-booking-id'
    mock_ssm, mock_secrets = mock_ssm_and_secrets

    mock_requests.post.return_value.status_code = 200
    mock_requests.post.return_value.json.return_value = {"message": "Booking confirmed"}

    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'consumerId': 'test-consumer-id',
            'oocpChargePointId': 'test-point-id',
            'system': 'Virta',
            'connectorId': '1',
            'startTime': '2024-12-30T12:00:00',
            'endTime': '2024-12-30T13:00:00'
        })
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    assert 'Slot booked successfully' in response['body']

def test_lambda_handler_failure(mock_requests, mock_ssm_and_secrets):
    mock_ssm, mock_secrets = mock_ssm_and_secrets

    mock_requests.post.return_value.status_code = 400
    mock_requests.post.return_value.text = "Invalid booking data"

    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'consumerId': 'test-consumer-id',
            'oocpChargePointId': 'test-point-id',
            'system': 'Virta',
            'connectorId': '1',
            'startTime': '2024-12-30T12:00:00',
            'endTime': '2024-12-30T13:00:00'
        })
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 500
    assert 'Invalid booking data' in response['body']

def test_lambda_handler_options_request():
    event = {'httpMethod': 'OPTIONS', 'body': None}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
