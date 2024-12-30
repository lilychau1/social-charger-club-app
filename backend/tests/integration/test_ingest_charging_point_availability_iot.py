import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from ingest_charging_point_availability_iot.app import lambda_handler, append_event_to_dynamodb
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
iot_client = boto3.client('iot-data')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['IngestChargingPointAvailabilityIoTFunction']['CHARGING_POINTS_TABLE_NAME']
        os.environ['CHARGING_POINT_EVENTS_TABLE_NAME'] = env_vars['IngestChargingPointAvailabilityIoTFunction']['CHARGING_POINT_EVENTS_TABLE_NAME']
        os.environ['IOT_ENDPOINT_URL'] = env_vars['IngestChargingPointAvailabilityIoTFunction']['IOT_ENDPOINT_URL']

load_env_vars()

@pytest.fixture(scope='module')
def test_event():
    return {
        'requestContext': {
            'routeKey': '$connect',
            'connectionId': 'mock-connection-id'
        },
        'body': json.dumps({
            'payload': {'chargePointId': 'mock-oocp-charge-point-id'}
        })
    }

@pytest.fixture(scope='module')
def test_message():
    return {
        'requestContext': {
            'routeKey': '$default',
            'connectionId': 'mock-connection-id'
        },
        'body': json.dumps({
            'action': 'StatusNotification',
            'payload': {'status': 'Available', 'chargePointId': 'mock-oocp-charge-point-id'}
        })
    }

def add_dummy_dynamodb_record(oocp_charge_point_id):
    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    item = {
        'chargingPointId': f'c-{oocp_charge_point_id}',
        'oocpChargePointId': oocp_charge_point_id,
        'producerId': f'p-{oocp_charge_point_id}', 
        'location': '(1, -1)', 
        'isConnected': False,
        'isAvailable': False,
        'statusUpdatedAt': datetime.now().isoformat(),
    }
    try:
        table.put_item(Item=item)
    except ClientError as e:
        print(f"Error adding DynamoDB record: {str(e)}")
        pytest.fail(f"Failed to add dummy record for {oocp_charge_point_id}")

def clean_up_dynamodb_item(oocp_charge_point_id):
    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    try:
        table.delete_item(
            Key={'oocpChargePointId': oocp_charge_point_id}
        )
    except ClientError as e:
        print(f"Error cleaning up DynamoDB item: {str(e)}")

def clean_up_charging_point_event(event_id):
    table = dynamodb.Table(os.environ['CHARGING_POINT_EVENTS_TABLE_NAME'])
    try:
        table.delete_item(
            Key={'eventId': event_id}
        )
    except ClientError as e:
        print(f"Error cleaning up DynamoDB event: {str(e)}")

def test_lambda_handler_connect(test_event):
    # Add dummy record before the test
    add_dummy_dynamodb_record('mock-oocp-charge-point-id')

    response = lambda_handler(test_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Connected'
    assert body['connectionId'] == 'mock-connection-id'
    assert body['oocpChargePointId'] == 'mock-oocp-charge-point-id'

    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    try:
        response = table.get_item(Key={'oocpChargePointId': 'mock-oocp-charge-point-id'})
        item = response.get('Item')
        assert item['isConnected'] is True
    except ClientError as e:
        pytest.fail(f"Error verifying DynamoDB item: {str(e)}")

    clean_up_dynamodb_item('mock-oocp-charge-point-id')

def test_lambda_handler_disconnect(test_event):
    test_event['requestContext']['routeKey'] = '$disconnect'

    add_dummy_dynamodb_record('mock-oocp-charge-point-id')

    response = lambda_handler(test_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Disconnected'
    assert body['connectionId'] == 'mock-connection-id'
    assert body['oocpChargePointId'] == 'mock-oocp-charge-point-id'

    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    try:
        response = table.get_item(Key={'oocpChargePointId': 'mock-oocp-charge-point-id'})
        item = response.get('Item')
        assert item['isDisconnected'] is True
    except ClientError as e:
        pytest.fail(f"Error verifying DynamoDB item: {str(e)}")

    clean_up_dynamodb_item('mock-oocp-charge-point-id')

def test_lambda_handler_message(test_message):
    add_dummy_dynamodb_record('mock-oocp-charge-point-id')

    response = lambda_handler(test_message, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == 'Message processed for action: StatusNotification'
    assert body['connectionId'] == 'mock-connection-id'

    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    try:
        response = table.get_item(Key={'oocpChargePointId': 'mock-oocp-charge-point-id'})
        item = response.get('Item')
        assert item['isAvailable'] is True
    except ClientError as e:
        pytest.fail(f"Error verifying DynamoDB item: {str(e)}")

    clean_up_dynamodb_item('mock-oocp-charge-point-id')

def test_append_event_to_dynamodb(test_message):
    message_body = json.loads(test_message['body'])
    event_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    append_event_to_dynamodb(
        message_body, 
        'mock-oocp-charge-point-id', 
        '$default', 
        'mock-connection-id', 
        event_id, 
        timestamp
    )

    table = dynamodb.Table(os.environ['CHARGING_POINT_EVENTS_TABLE_NAME'])
    try:
        response = table.get_item(Key={'eventId': event_id})
        item = response.get('Item')
        assert item['eventId'] == event_id
        assert item['oocpChargePointId'] == 'mock-oocp-charge-point-id'
        assert item['eventType'] == 'default'
    except ClientError as e:
        pytest.fail(f"Error verifying DynamoDB event: {str(e)}")

    clean_up_charging_point_event(event_id)

if __name__ == '__main__':
    pytest.main([__file__])
