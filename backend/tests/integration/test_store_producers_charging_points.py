import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from store_producers_charging_points.app import lambda_handler

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Load environment variables from the env-vars.json file
def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['StoreProducersChargingPointsFunction']['CHARGING_POINTS_TABLE_NAME']

# Call this function before your tests (to ensure environment variables are set)
load_env_vars()

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
def clean_up_charging_points():
    # Cleanup function to remove test data from DynamoDB after tests run
    table_name = os.environ['CHARGING_POINTS_TABLE_NAME']
    table = dynamodb.Table(table_name)

    def clean_up(charging_point_ids):
        for charging_point_id in charging_point_ids:
            try:
                table.delete_item(
                    Key={'chargingPointId': charging_point_id}  # Adjust based on your actual key structure
                )
                print(f"Deleted charging point with ID: {charging_point_id}")
            except ClientError as e:
                print(f"Failed to delete charging point {charging_point_id}: {e.response['Error']['Message']}")

    yield clean_up

# Integration tests
def test_lambda_handler_integration(test_charging_point, clean_up_charging_points):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(test_charging_point)
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "Charging points added successfully"
    charging_point_ids = body['chargingPointIds']
    
    # Verify that the charging point was added to DynamoDB
    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    
    # Check if the charging point exists in the table (you may need to adjust this based on your schema)
    for charging_point_id in charging_point_ids:
        response = table.get_item(
            Key={'chargingPointId': charging_point_id}  # Adjust based on your actual key structure
        )
        assert response.get('Item') is not None

    # Clean up after the test (implement cleanup logic)
    clean_up_charging_points(charging_point_ids)

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
