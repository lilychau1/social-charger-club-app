import json
import os
import boto3
import pytest
from get_charging_points.app import lambda_handler

@pytest.fixture(scope='module')
def dynamodb_table():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    
    # Add test data
    test_data = [
        {
            'oocpChargePointId': 'test-cp1',
            'chargingPointId': 'test-cp1',
            'stationName': 'Test Station A',
            'primaryElectricitySource': 'Solar',
            'location': '51.5074,-0.1278'  # London
        },
        {
            'oocpChargePointId': 'test-cp2',
            'chargingPointId': 'test-cp2',
            'stationName': 'Test Station B',
            'primaryElectricitySource': 'Grid',
            'location': '55.9533,-3.1883'  # Edinburgh
        },
        {
            'oocpChargePointId': 'test-cp3',
            'chargingPointId': 'test-cp3',
            'stationName': 'Test Station C',
            'primaryElectricitySource': 'Wind',
            'location': '51.5014,-0.1419'  # London (close to test-cp1)
        }
    ]
    
    for item in test_data:
        table.put_item(Item=item)

    yield table
    
    # Clean up test data
    for item in test_data:
        table.delete_item(Key={'oocpChargePointId': item['oocpChargePointId']})

def test_integration_lambda_handler_success(dynamodb_table):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'SW1A 1AA',  # London
            'radius': 10
        })
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) > 0

    assert any(point['chargingPointId'] == 'test-cp1' for point in body)
    assert any(point['chargingPointId'] == 'test-cp3' for point in body)
    assert all(point['chargingPointId'] != 'test-cp2' for point in body)

def test_integration_lambda_handler_no_results(dynamodb_table):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'EH1 1YZ',  # Edinburgh
            'radius': 0.1  # Small radius to ensure no results
        })
    }
    
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) == 0

def test_integration_lambda_handler_invalid_postcode(dynamodb_table):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'INVALID',
            'radius': 10
        })
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'Invalid postcode' in body['error']

def test_integration_lambda_handler_missing_postcode(dynamodb_table):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'radius': 10
        })
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_integration_lambda_handler_options_request(dynamodb_table):
    event = {
        'httpMethod': 'OPTIONS'
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']

def test_integration_lambda_handler_default_radius(dynamodb_table):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'SW1A 1AA'  # London, no radius specified
        })
    }
    
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert len(body) > 0  # Should use default radius of 5 miles

