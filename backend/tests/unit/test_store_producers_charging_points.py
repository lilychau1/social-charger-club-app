import json
import os
import pytest
from botocore.exceptions import ClientError
from unittest.mock import patch, MagicMock
from lambda_functions.store_producers_charging_points.app import lambda_handler

# Fixture to create a mock API Gateway event
@pytest.fixture()
def apigw_event():
    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "producerId": "testProducer",
            "chargingPoints": [
                {
                    "stationName": "Station A",
                    "address": "123 Main St",
                    "latitude": "40.7128",
                    "longitude": "-74.0060",
                    "chargingSpeed": ["Level 2", "Level 3"],
                    "connectorTypes": ["SAE J1772", "CCS"],
                    "maxPowerOutputAC": '22',
                    "maxPowerOutputDC": '150',
                    "numChargingPoints": '4',
                    "paymentMethods": ['RFID Card', 'Mobile App'],
                    "operatingHours": '24/7',
                    "parkingType": 'Street',
                    "networkProvider": 'ChargePoint',
                    "userInterface": 'Yes',
                    "cableManagement": 'Yes',
                    "weatherProtection": 'No',
                    "primaryElectricitySource": ['Grid', 'Solar'],
                    "renewablePercentage": 30
                }
            ]
        })
    }

@patch('lambda_functions.store_producers_charging_points.app.dynamodb')
def test_lambda_handler_success(mock_dynamodb, apigw_event):
    # Mock the put_item method to simulate successful insertion
    mock_dynamodb.put_item.return_value = {}

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "Charging points added successfully"
    mock_dynamodb.put_item.assert_called()  # Ensure put_item was called

@patch('lambda_functions.store_producers_charging_points.app.dynamodb')
def test_lambda_handler_missing_latitude(mock_dynamodb, apigw_event):
    # Modify the event to remove latitude
    event = {
        **apigw_event,
        'body': json.dumps({
            "producerId": "testProducer",
            "chargingPoints": [
                {
                    "stationName": "Station B",
                    "address": "456 Elm St",
                    # Missing latitude
                    "longitude": "-74.0060"
                }
            ]
        })
    }

    response = lambda_handler(event, "")

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Both latitude and longitude are required."

@patch('lambda_functions.store_producers_charging_points.app.dynamodb')
def test_lambda_handler_invalid_json(mock_dynamodb):
    event = {
        'httpMethod': 'POST',
        'body': None  # Invalid JSON structure (missing body)
    }

    response = lambda_handler(event, "")

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Invalid input. producerId and chargingPoints are required."

@patch('lambda_functions.store_producers_charging_points.app.dynamodb')
def test_lambda_handler_no_producer_id(mock_dynamodb, apigw_event):
    # Modify the event to remove producerId
    event = {
        **apigw_event,
        'body': json.dumps({
            # Missing producerId
            "chargingPoints": [
                {
                    "stationName": "Station C",
                    "address": "789 Oak St",
                    "latitude": "40.7128",
                    "longitude": "-74.0060"
                }
            ]
        })
    }

    response = lambda_handler(event, "")

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Invalid input. producerId and chargingPoints are required."

@patch('lambda_functions.store_producers_charging_points.app.dynamodb')
def test_lambda_handler_dynamodb_error(mock_dynamodb, apigw_event):
    mock_dynamodb.put_item.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", 
                   "Message": "Requested resource not found"}},
        operation_name='PutItem'
    )

    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 500
    body = json.loads(response['body'])
    assert 'error' in body

def test_lambda_handler_options(apigw_event):
    apigw_event['httpMethod'] = 'OPTIONS'
    
    response = lambda_handler(apigw_event, "")

    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
