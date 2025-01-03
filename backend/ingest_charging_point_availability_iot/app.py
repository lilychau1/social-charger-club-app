import json
import boto3
import os
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
charging_points_table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME'))
charging_point_events_table = dynamodb.Table(os.environ.get('CHARGING_POINT_EVENTS_TABLE_NAME'))

cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def lambda_handler(event, context):

    # Handle CORS preflight requests (OPTIONS)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_header
        }
        
    for record in event['Records']:
        # Extract MQTT topic and message
        topic = record['topic']
        message_body = json.loads(record['message'])
        try:
            oocp_charge_point_id = extract_oocp_charge_point_id_from_topic(topic)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': cors_header, 
                'body': json.dumps({'error': str(e)})
            }

        if topic.endswith('/status'):
            # Handle connect / disconnect or status updates
            status = message_body.get('status')
            if not status:
                return {
                    'statusCode': 400,
                    'headers': cors_header, 
                    'body': json.dumps({'error': 'Invalid status field in message.'})
                }
            handle_device_status(oocp_charge_point_id, status)
        else:
            # Handle other actions (e.g., StartTransaction, StopTransaction)
            action = message_body.get('action')
            handle_action(action, oocp_charge_point_id, message_body)

    return {
        'statusCode': 200,
        'headers': cors_header, 
        'body': json.dumps({'message': 'Messages processed successfully'})
    }

def extract_oocp_charge_point_id_from_topic(topic):
    """
    Extract the device ID from the MQTT topic.
    Assumes topic format: "charging_points/<oocp_charge_point_id>/<action>"
    """
    try:
        oocp_charge_point_id = topic.split('/')[1]
        if not oocp_charge_point_id:
            raise ValueError("oocpChargePointId is missing")
        return oocp_charge_point_id
    except IndexError:
        raise ValueError("Invalid topic format")

def handle_device_status(oocp_charge_point_id, status):
    """
    Process connect or disconnect events based on the status message.
    """
    timestamp = datetime.now().isoformat()
    is_connected = status == "online"

    # Update the ChargingPoints table
    charging_points_table.update_item(
        Key={'oocpChargePointId': oocp_charge_point_id},
        UpdateExpression=(
            'SET isConnected = :connected, '
            'statusUpdatedAt = :timestamp'
        ),
        ExpressionAttributeValues={
            ':connected': is_connected,
            ':timestamp': timestamp
        }
    )

    charging_point_events_table.put_item(Item={
        'eventId': str(uuid.uuid4()),
        'oocpChargePointId': oocp_charge_point_id,
        'timestamp': timestamp,
        'eventType': 'connect' if is_connected else 'disconnect',
        'message': {'status': status}
    })

def handle_action(action, oocp_charge_point_id, message_body):
    """
    Process specific actions sent from the device, such as StartTransaction or StatusNotification.
    """
    timestamp = datetime.now().isoformat()

    if action == 'StatusNotification':
        status = message_body.get('payload', {}).get('status')
        is_available = (status == 'Available')
    elif action == 'StartTransaction':
        is_available = False
    elif action == 'StopTransaction':
        is_available = True
    else:
        # Log and skip unknown actions
        charging_point_events_table.put_item(Item={
            'eventId': str(uuid.uuid4()),
            'oocpChargePointId': oocp_charge_point_id,
            'timestamp': timestamp,
            'eventType': action,
            'message': message_body
        })

    # Update the ChargingPoints table with the new availability status
    charging_points_table.update_item(
        Key={'oocpChargePointId': oocp_charge_point_id},
        UpdateExpression=(
            'SET isAvailable = :available, '
            'statusUpdatedAt = :timestamp'
        ),
        ExpressionAttributeValues={
            ':available': is_available,
            ':timestamp': timestamp
        }
    )

    # Log the action event in ChargingPointEvents table
    charging_point_events_table.put_item(Item={
        'eventId': str(uuid.uuid4()),
        'oocpChargePointId': oocp_charge_point_id,
        'timestamp': timestamp,
        'eventType': action,
        'message': message_body
    })
