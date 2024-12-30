import json
import boto3
import os
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
charging_points_table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME'))
charging_point_events_table = dynamodb.Table(os.environ.get('CHARGING_POINT_EVENTS_TABLE_NAME'))
iot_client = boto3.client(
    'iot-data', 
    endpoint_url=os.environ.get('IOT_ENDPOINT_URL')
)

def lambda_handler(event, context): 
    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']
    
    event_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    message_body = json.loads(event['body'])
    oocp_charge_point_id = message_body.get('payload', {}).get('chargePointId')
    
    # Store events to events table
    append_event_to_dynamodb(
        message_body, 
        oocp_charge_point_id, 
        route_key, 
        connection_id, 
        event_id, 
        timestamp
    )
    
    if route_key == '$connect':
        return handle_connect(connection_id, oocp_charge_point_id, timestamp)
    if route_key == '$disconnect': 
        return handle_disconnect(connection_id, oocp_charge_point_id, timestamp)
    if route_key == '$default': 
        return handle_message(connection_id, oocp_charge_point_id, timestamp, message_body)

def append_event_to_dynamodb(message_body, oocp_charge_point_id, route_key, connection_id, event_id, timestamp):
    charging_point_events_table.put_item(Item={
        'eventId': event_id, 
        'oocpChargePointId': oocp_charge_point_id, 
        'timestamp': timestamp, 
        'connectionId': connection_id, 
        'eventType': route_key.replace('$', ''), 
        'message': message_body
    })
    
def handle_connect(connection_id, oocp_charge_point_id, timestamp): 
    breakpoint()
    charging_points_table.update_item(
        Key={'oocpChargePointId': oocp_charge_point_id}, 
        UpdateExpression='SET  isConnected = :connected, statusUpdatedAt = :timestamp', 
        ExpressionAttributeValues={
            ':connected': True, 
            ':timestamp': timestamp
        }
    )
    return {
        'statusCode': 200, 
        'body': json.dumps({
            'message': 'Connected', 
            'connectionId': connection_id, 
            'oocpChargePointId': oocp_charge_point_id, 
        })
    }

def handle_disconnect(connection_id, oocp_charge_point_id, timestamp): 
    charging_points_table.update_item(
        Key={'oocpChargePointId': oocp_charge_point_id}, 
        UpdateExpression='SET  isDisconnected = :disconnected, statusUpdatedAt = :timestamp', 
        ExpressionAttributeValues={
            ':disconnected': True, 
            ':timestamp': timestamp
        }
    )
    return {
        'statusCode': 200, 
        'body': json.dumps({
            'message': 'Disconnected', 
            'connectionId': connection_id, 
            'oocpChargePointId': oocp_charge_point_id, 
        })
    }

def handle_message(connection_id, oocp_charge_point_id, timestamp, message_body): 
    breakpoint()
    action = message_body.get('action')
    
    if action == 'StatusNotification': 
        status = message_body.get('payload', {}).get('status')
        
        if status == 'Available': 
            is_available = True
        elif status == 'Charging':
            is_available = False
        elif status == 'Reserved':
            is_available = False
        else:
            is_available = False

    elif action == 'StartTransaction':
        is_available = False
        
    elif action == 'StopTransaction':
        is_available = True
    else: 
        return {
            'statusCode': 200, 
            'body': json.dumps({'message': f'No actions taken for action: {action}', 'connectionId': connection_id})
        }

    # Update the ChargingPoints table with the new availability and timestamps
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
    
    return {
        'statusCode': 200, 
        'body': json.dumps({'message': f'Message processed for action: {action}', 'connectionId': connection_id})
    }