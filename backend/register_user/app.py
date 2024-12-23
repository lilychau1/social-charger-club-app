import json
import boto3
import uuid
import os
from typing import Tuple
from botocore.exceptions import ClientError

from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')
table_name = 'EVCharging_Users'
table = dynamodb.Table(table_name)
user_pool_id = os.environ.get('USER_POOL_ID', None)
client_id = os.environ.get('USER_POOL_CLIENT_ID', None)

cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def generate_ids(user_type: str) -> Tuple[str, str, str]:
    # Generate UUIDs for user_id, consumer_id, and producer_id
    user_uuid = str(uuid.uuid4())
    consumer_uuid = str(uuid.uuid4()) if user_type in ('consumer', 'prosumer') else None
    producer_uuid = str(uuid.uuid4()) if user_type in ('producer', 'prosumer') else None
    return user_uuid, consumer_uuid, producer_uuid

def create_cognito_user(
    email, 
    password, 
    username, 
    user_type, 
    user_id, 
    consumer_id=None, 
    producer_id=None
): 
    cognito_resp = cognito.sign_up(
        ClientId=client_id, 
        Username=email, 
        Password=password, 
        UserAttributes=[
            {'Name': 'email', 'Value': email}, 
            {'Name': 'preferred_username', 'Value': username},
            {'Name': 'custom:userType', 'Value': user_type},
            {'Name': 'custom:userId', 'Value': user_id}
        ] 
        + [{'Name': 'custom:consumerId', 'Value': consumer_id}] if consumer_id else [] # record consumer_id if it is not null
        + [{'Name': 'custom:producerId', 'Value': producer_id}] if producer_id else [] # record producer_id if it is not null
    )
    return cognito_resp

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    # Handle CORS preflight requests (OPTIONS)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_header
        }

    try:
        # Parse the body from the event
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        # Use email as the default username
        password = body.get('password')
        username = body.get('username', email)
        user_type = body.get('user_type')

        # Generate IDs
        user_id, consumer_id, producer_id = generate_ids(user_type)

        # Create cognito user
        try: 
            cognito_resp = create_cognito_user(
                email,
                password,
                username,
                user_type,
                user_id,
                consumer_id,
                producer_id
            )
        except ClientError as e:
            return {
                'statusCode': 400,
                'headers': cors_header,
                'body': json.dumps({'error': str(e)})
            }
        
        # Create item for DynamoDB
        item = {
            'user_id': user_id,
            'email': email,
            'username': username,
            'user_type': user_type,
            'consumer_id': consumer_id,
            'producer_id': producer_id,
            'created_at': datetime.now().isoformat(),
            'status': 'UNVERIFIED'
        }

        # Store item in DynamoDB
        table.put_item(Item=item)

        # Return success response
        return {
            'statusCode': 200,
            'headers': cors_header,
            'body': json.dumps({
                'user_id': user_id,
                'consumer_id': consumer_id,
                'producer_id': producer_id,
                'message': f"User data for {username} (user_id: {user_id}) stored successfully."
            })
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*', 
                'Access-Control-Allow-Methods': '*',
                'Access-Control-Allow-Headers': '*'
            },
            'body': json.dumps({
                'error': str(e) or "Unable to store user in DynamoDB."
            })
        }
