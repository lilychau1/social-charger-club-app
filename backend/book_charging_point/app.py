import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
charging_points_table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME', 'default-charging-points-table'))
api_gateway_client = boto3.client('apigateway')

ssm_client = boto3.client('ssm')
secrets_client = boto3.client('secretsmanager')

secret_name = os.environ.get('SECRET_NAME')
PARAMETER_PREFIX = os.environ.get('PARAMETER_PREFIX')

cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_header
        }
        
    try:
        if 'body' in event:
            event_body = json.loads(event['body'])
        else:
            raise ValueError("Missing 'body' field in event.")

        required_fields = ['oocpChargePointId', 'system', 'connectorId', 'startTime', 'endTime']
        if not all(field in event_body for field in required_fields):
            raise ValueError("Missing required input fields.")

        oocp_charge_point_id = event_body['oocpChargePointId']
        system = event_body['system']
        connector_id = event_body['connectorId']
        start_time = event_body['startTime']
        end_time = event_body['endTime']

        reservation_response = send_oocp_reservation_request(system, oocp_charge_point_id, connector_id, start_time, end_time)
        
        if reservation_response.get('status') == 'success':
            update_dynamodb_status(oocp_charge_point_id, False)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Slot booked successfully, charging point is now unavailable.'})
            }
        else:
            raise Exception(f"Reservation failed: {reservation_response.get('message')}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def update_dynamodb_status(oocp_charge_point_id, is_available):
    try:
        charging_points_table.update_item(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression="SET isAvailable = :is_available, statusUpdatedAt = :timestamp",
            ExpressionAttributeValues={
                ':is_available': is_available,
                ':timestamp': datetime.now().isoformat()
            },
            ConditionExpression="attribute_exists(oocpChargePointId)"
        )
    except ClientError as e:
        raise Exception(f"Error updating DynamoDB: {e.response['Error']['Message']}")

def get_api_gateway_url(system):
    if system == 'Virta':
        return get_parameter_or_secret('VIRTA_API_GATEWAY_URL')
    elif system == 'EVBox':
        return get_parameter_or_secret('EVBOX_API_GATEWAY_URL')
    elif system in ['Siemens', 'Schneider Electric']:
        return get_parameter_or_secret('GENERIC_CPO_API_GATEWAY_URL')
    return None

def get_parameter_or_secret(param_name):
    value = os.environ.get(param_name)
    if not value:
        if 'KEY' in param_name:
            value = get_secret_value(param_name)
        else:
            value = get_ssm_parameter(PARAMETER_PREFIX + param_name)
    if not value:
        raise ValueError(f"{param_name} not found in environment, SSM, or Secrets Manager.")
    return value

def get_ssm_parameter(param_name):
    try:
        response = ssm_client.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except ClientError as e:
        print(f"Error fetching {param_name} from SSM: {str(e)}")
        return None

def get_secret_value(secret_key):
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)

        if 'SecretString' in response:
            return json.loads(response['SecretString']).get(secret_key)
        else:
            return json.loads(response['SecretBinary']).get(secret_key)
    except ClientError as e:
        print(f"Error fetching {secret_key} from Secrets Manager: {str(e)}")
        return None

def send_oocp_reservation_request(system, oocp_charge_point_id, connector_id, start_time, end_time):
    api_url = get_api_gateway_url(system)
    if not api_url:
        raise ValueError(f"No API Gateway URL configured for system: {system}")

    headers = {
        'Content-Type': 'application/json',
        **get_auth(system)
    }
    payload = {
        'chargePointId': oocp_charge_point_id,
        'connectorId': connector_id,
        'startTime': start_time,
        'endTime': end_time
    }

    try:
        response = api_gateway_client.test_invoke_method(
            restApiId=os.environ.get('API_GATEWAY_ID'),
            resourceId=get_parameter_or_secret(f'{system.upper()}_RESOURCE_ID'),
            httpMethod='POST',
            headers=headers,
            body=json.dumps(payload)
        )
        response_body = json.loads(response['body'])
        if response['status'] == 200:
            return {'status': 'success', 'message': response_body}
        else:
            raise Exception(f"API Gateway call failed: {response_body}")
    except ClientError as e:
        raise Exception(f"Error invoking API Gateway: {str(e)}")

def get_auth(system):
    if system == 'Virta':
        return {'X-API-Key': get_parameter_or_secret('VIRTA_API_KEY')}
    elif system == 'ChargePoint':
        return {'Authorization': f"Bearer {get_parameter_or_secret('CHARGEPOINT_API_TOKEN')}"}
    elif system == 'EVBox':
        return {'Authorization': f"Bearer {get_parameter_or_secret('EVBOX_TOKEN')}"}
    elif system in ['Siemens', 'Schneider Electric']:
        return {'Authorization': f"Bearer {get_parameter_or_secret('GENERIC_CPO_TOKEN')}"}
    return {}
