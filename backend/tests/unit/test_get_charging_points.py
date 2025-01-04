import json
import pytest
from unittest.mock import patch, MagicMock
from lambda_functions.get_charging_points.app import lambda_handler, get_lat_long_from_postcode

@pytest.fixture
def mock_dynamodb_table():
    with patch('lambda_functions.get_charging_points.app.table') as mock_table:
        mock_table.scan.return_value = {
        'Items': [
            {
                'chargingPointId': 'cp1',
                'stationName': 'Station A', 
                'primaryElectricitySource': 'Solar', 
                'location': '51.5074,-0.1278', 
                'currentChargingConsumerId': 'mock-consumer-id-1', 
                'isAvailable': True, 
            },
            {
                'chargingPointId': 'cp2', 
                'stationName': 'Station B', 
                'primaryElectricitySource': 'Grid', 
                'location': '55.9533,-3.1883', 
                'currentChargingConsumerId': 'mock-consumer-id-2', 
                'isAvailable': False, 
            }
        ]
    }

        yield mock_table

@pytest.fixture
def mock_geocoder():
    with patch('lambda_functions.get_charging_points.app.Nominatim') as mock_nom:
        mock_location = MagicMock()
        mock_location.latitude = 51.5074
        mock_location.longitude = -0.1278
        mock_nom.return_value.geocode.return_value = mock_location
        yield mock_nom

def test_get_lat_long_from_postcode(mock_geocoder):
    result = get_lat_long_from_postcode('SW1A 1AA')
    assert result == (51.5074, -0.1278)

def test_lambda_handler_success(mock_dynamodb_table, mock_geocoder):
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'SW1A 1AA',
            'radius': 10
        })
    }
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])

    assert len(body) == 1
    assert body[0]['chargingPointId'] == 'cp1'

def test_lambda_handler_invalid_postcode(mock_dynamodb_table, mock_geocoder):
    mock_geocoder.return_value.geocode.return_value = None
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'postcode': 'INVALID',
            'radius': 10
        })
    }
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 400
    assert 'Invalid postcode' in response['body']

def test_lambda_handler_options_request():
    event = {'httpMethod': 'OPTIONS'}
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
