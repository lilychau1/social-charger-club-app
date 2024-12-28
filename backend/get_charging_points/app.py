import json
import boto3
import os
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
from typing import Tuple
import re

def is_valid_postcode(postcode):
    # Add regex patterns for valid UK postcode formats
    uk_pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2}$'
    
    return re.match(uk_pattern, postcode.upper()) is not None

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('CHARGING_POINTS_TABLE_NAME')
table = dynamodb.Table(table_name)

options_headers = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def get_lat_long_from_postcode(postcode: str) -> Tuple[float, float]:
    if (not postcode) or (not is_valid_postcode(postcode)):
        return None
    
    geolocator = Nominatim(user_agent="social-charger-club-app")
    location = geolocator.geocode(postcode)
    return (location.latitude, location.longitude) if location else None

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": options_headers, 
            "body": json.dumps({})
        }

    try: 
        body = json.loads(event.get('body', '{}'))
        postcode = body.get('postcode')
        # Get radius with default value of 5 miles
        radius = body.get('radius', 5)

        lat_long = get_lat_long_from_postcode(postcode)
        
        if not lat_long:
            return {
                'statusCode': 400, 
                'body': json.dumps({'error': 'Invalid postcode.'})
            }
        
        user_lat_long = lat_long
        print(f'User Location: {user_lat_long}')

        response = table.scan()
        charging_points = response.get('Items', [])
        
        nearby_charging_points = []
        for point in charging_points:
            point_location = point['location'].split(',')
            point_lat_long = (float(point_location[0]), float(point_location[1]))
            distance = great_circle(user_lat_long, point_lat_long).miles
            
            if distance <= radius: 
                nearby_charging_points.append({
                    'chargingPointId': point['chargingPointId'], 
                    'stationName': point['stationName'], 
                    'primaryElectricitySource': point['primaryElectricitySource'], 
                })

        return {
            'statusCode': 200, 
            'headers': options_headers, 
            'body': json.dumps(nearby_charging_points)
        }
            
    except Exception as e: 
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500, 
            'headers': options_headers, 
            'body': json.dumps({'error': str(e)})
        }