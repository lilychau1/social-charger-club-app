import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from lambda_functions.store_producers_charging_points.app import lambda_handler

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['StoreProducersChargingPointsFunction']['CHARGING_POINTS_TABLE_NAME']


load_env_vars()

oocp_charge_point_id = 'mock-oocp-charge-point-id'
oocp_charge_point_ids = [oocp_charge_point_id]

@pytest.fixture(scope='module')
def test_charging_point():
    return {
        'producerId': 'testProducer',
        'chargingPoints': [
            {
                'stationName': 'Station A',
                'address': '123 Main St',
                'latitude': '40.7128',
                'longitude': '-74.0060',
                'oocpChargePointId': oocp_charge_point_id, 
                'chargingSpeed': ['Level 2', 'Level 3'],
                'connectorTypes': ['SAE J1772', 'CCS'],
                'maxPowerOutputAC': '22',
                'maxPowerOutputDC': '150',
                'numChargingPoints': '4',
                'paymentMethods': ['RFID Card', 'Mobile App'],
                'operatingHours': '24/7',
                'parkingType': 'Street',
                'networkProvider': 'ChargePoint',
                'userInterface': 'Yes',
                'cableManagement': 'Yes',
                'weatherProtection': 'No',
                'primaryElectricitySource': ['Grid', 'Solar'],
                'renewablePercentage': 30
            }
        ]
    }

@pytest.fixture(scope='module')
def dynamodb_table_charging_points():
    table_name = os.environ['CHARGING_POINTS_TABLE_NAME']
    table = dynamodb.Table(table_name)
    yield table

    for id in oocp_charge_point_ids:
        try:
            table.delete_item(
                Key={'oocpChargePointId': id}
            )
            print(f"Deleted charging point with ID: {id}")
        except ClientError as e:
            print(f"Failed to delete charging point {id}: {e.response['Error']['Message']}")

# Integration tests
def test_lambda_handler_integration(test_charging_point, dynamodb_table_charging_points):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(test_charging_point)
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "Charging points added successfully"
    
    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    
    for id in oocp_charge_point_ids:
        response = table.get_item(
            Key={'oocpChargePointId': id}
        )
        assert response.get('Item') is not None

def test_lambda_handler_missing_fields():
    missing_fields_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            "producerId": "testProducer",
            "chargingPoints": [
                {
                    "stationName": "Station B",
                    # Missing latitude and longitude fields
                }
            ]
        })
    }

    response = lambda_handler(missing_fields_event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Both latitude and longitude are required."

def test_lambda_handler_invalid_request():
    invalid_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            "producerId": "testProducer",
            "chargingPoints": [
                {
                    "stationName": "Station C",
                    # Missing required fields (e.g., latitude, longitude)
                    # You can add more invalid scenarios here.
                }
            ]
        })
    }

    response = lambda_handler(invalid_event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert "error" in body

if __name__ == '__main__':
    pytest.main([__file__])