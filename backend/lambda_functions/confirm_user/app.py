import json
import boto3
import uuid
import os
from typing import Tuple
from botocore.exceptions import ClientError

from datetime import datetime

cognito = boto3.client('cognito-idp')
user_pool_id = os.environ.get('USER_POOL_ID')
client_id = os.environ.get('USER_POOL_CLIENT_ID')

cors_headers = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def lambda_handler(event, context):
    # Handle CORS preflight requests (OPTIONS)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers, 
            'body': json.dumps({'message': 'OPTIONS request'})
        }

    try:
        event_body = json.loads(event.get('body', '{}'))

        email = event_body.get('email')
        confirmation_code = event_body.get('confirmationCode')
        
        if not email or not confirmation_code:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing email or confirmation code.'})
            }

        # Confirm the user using the confirmation code
        response = cognito.confirm_sign_up(
            ClientId=client_id,
            Username=email,
            ConfirmationCode=confirmation_code
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'User confirmed successfully.', 'response': response})
        }

    except ClientError as e:
        error_message = e.response['Error']['Message']
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': error_message})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
        
