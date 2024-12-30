import json
import os
import boto3
import pytest
from botocore.exceptions import ClientError
from ingest_charging_point_availability_iot.app import lambda_handler  # Replace with the actual module path

dynamodb = boto3.resource('dynamodb')

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['CHARGING_POINTS_TABLE_NAME'] = env_vars['StoreProducersChargingPointsFunction']['CHARGING_POINTS_TABLE_NAME']
        os.environ['CHARGING_POINT_EVENTS_TABLE_NAME'] = env_vars['StoreProducersChargingPointsFunction']['CHARGING_POINT_EVENTS_TABLE_NAME']

load_env_vars()

@pytest.fixture(scope='module')
def test_mqtt_message():
    return {
        'Records': [
            {
                'topic': 'charging_points/C123456/status',
                'message': json.dumps({'status': 'online'})
            },
            {
                'topic': 'charging_points/C123456/action',
                'message': json.dumps({'action': 'StartTransaction'})
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
                    Key={'oocpChargePointId': charging_point_id}
                )
                print(f"Deleted charging point with ID: {charging_point_id}")
            except ClientError as e:
                print(f"Failed to delete charging point {charging_point_id}: {e.response['Error']['Message']}")

    yield clean_up

# Integration tests
def test_lambda_handler_mqtt_integration(test_mqtt_message, clean_up_charging_points):
    response = lambda_handler(test_mqtt_message, None)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "Messages processed successfully"

    table = dynamodb.Table(os.environ['CHARGING_POINTS_TABLE_NAME'])
    for record in test_mqtt_message['Records']:
        oocp_charge_point_id = record['topic'].split('/')[1]
        response = table.get_item(
            Key={'oocpChargePointId': oocp_charge_point_id}
        )
        assert response.get('Item') is not None

    clean_up_charging_points([record['topic'].split('/')[1] for record in test_mqtt_message['Records']])

def test_lambda_handler_missing_fields():
    missing_fields_event = {
        'Records': [
            {
                'topic': 'charging_points/C123456/status',
                'message': json.dumps({'status': None})
            }
        ]
    }

    response = lambda_handler(missing_fields_event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == "Invalid status field in message."

def test_lambda_handler_invalid_topic():
    invalid_event = {
        'Records': [
            {
                'topic': 'invalid_topic_format',
                'message': json.dumps({'status': 'online'})
            }
        ]
    }

    response = lambda_handler(invalid_event, None)
    
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert "Invalid topic format" in body['error']

def test_lambda_handler_unknown_action():
    unknown_action_event = {
        'Records': [
            {
                'topic': 'charging_points/C123456/action',
                'message': json.dumps({'action': 'UnknownAction'})
            }
        ]
    }

    response = lambda_handler(unknown_action_event, None)
    
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['message'] == "Messages processed successfully"

    events_table = dynamodb.Table(os.environ['CHARGING_POINT_EVENTS_TABLE_NAME'])
    oocp_charge_point_id = 'C123456'
    response = events_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('oocpChargePointId').eq(oocp_charge_point_id)
    )
    assert any(event.get('eventType') == 'UnknownAction' for event in response.get('Items', []))

if __name__ == '__main__':
    pytest.main([__file__])
