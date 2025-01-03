import json
import pytest
from unittest.mock import MagicMock, patch
import os
import boto3
from botocore.exceptions import ClientError
from lambda_functions.book_charging_point.app import lambda_handler, send_oocp_reservation_request

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['BookChargingPointFunction']['CHARGING_POINTS_TABLE_NAME']
        os.environ['BOOKINGS_TABLE_NAME'] = env_vars['BookChargingPointFunction']['BOOKINGS_TABLE_NAME']
        os.environ['PARAMETER_PREFIX'] = env_vars['BookChargingPointFunction']['PARAMETER_PREFIX']
        os.environ['SECRET_NAME'] = env_vars['BookChargingPointFunction']['SECRET_NAME']
        os.environ['API_GATEWAY_ID'] = env_vars['BookChargingPointFunction']['API_GATEWAY_ID']

load_env_vars()

@pytest.fixture(scope='module')
def dynamodb_table_charging_points():
    table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME'))
    
    test_data = {
        'oocpChargePointId': 'test-point-id',
        'isAvailable': True,
        'statusUpdatedAt': '2024-12-30T00:00:00'
    }
    
    table.put_item(Item=test_data)

    yield table
    
    table.delete_item(Key={'oocpChargePointId': test_data['oocpChargePointId']})

mock_booking_id = 'mock-booking_id'

@pytest.fixture(scope='module')
def dynamodb_table_bookings():
    table = dynamodb.Table(os.environ['BOOKINGS_TABLE_NAME'])

    yield table
    
    # Clean up test data
    table.delete_item(Key={'bookingId': mock_booking_id})

@pytest.fixture
def mock_api_gateway_client():
    with patch('lambda_functions.book_charging_point.app.api_gateway_client') as mock_client:
        mock_api_response = {
            'status': 200, 
            'body': '{"result": "success"}'
        }
        mock_client.test_invoke_method.return_value = mock_api_response
        yield mock_client

def test_send_oocp_reservation_request_virta(mock_api_gateway_client):
    response = send_oocp_reservation_request(
        'Virta', 'test-point-id', '1', '2024-12-30T12:00:00', '2024-12-30T13:00:00'
    )
    assert response['status'] == 'success'
    mock_api_gateway_client.test_invoke_method.assert_called_once()

def test_send_oocp_reservation_request_unsupported_system():
    # Create event data with an unsupported system
    event_body = {
        'oocpChargePointId': 'test-point-id',
        'system': 'UnknownSystem',
        'connectorId': '1',
        'startTime': '2024-12-30T12:00:00',
        'endTime': '2024-12-30T13:00:00'
    }

    # Call the function to test
    with pytest.raises(ValueError):
        send_oocp_reservation_request(
            event_body['system'],
            event_body['oocpChargePointId'],
            event_body['connectorId'],
            event_body['startTime'],
            event_body['endTime']
        )

@patch('lambda_functions.book_charging_point.app.uuid')
def test_lambda_handler_success(mock_uuid, mock_api_gateway_client, dynamodb_table_charging_points, dynamodb_table_bookings):
    mock_uuid.uuid4.return_value = mock_booking_id
    event = {
        'httpMethod': 'POST', 
        'body': "{\"consumerId\": \"test-consumer-id\", \"oocpChargePointId\": \"test-point-id\", \"system\": \"Virta\", \"connectorId\": \"1\", \"startTime\": \"2024-12-30T12:00:00\", \"endTime\": \"2024-12-30T13:00:00\"}"
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    assert 'Slot booked successfully' in response['body']

def test_lambda_handler_options_request():
    event = {'httpMethod': 'OPTIONS', 'body': None}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
