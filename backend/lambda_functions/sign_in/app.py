import json
import boto3
from botocore.exceptions import ClientError
import os

# Initialize the Cognito client
cognito = boto3.client('cognito-idp')

user_pool_id = os.environ.get('USER_POOL_ID')
client_id = os.environ.get('USER_POOL_CLIENT_ID')

# Set CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',  # Frontend URL
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def lambda_handler(event, context):
    # Handle OPTIONS request for CORS
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'OPTIONS request'})
        }

    try:
        # Parse the incoming request
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')

        if not email or not password:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing email or password.'})
            }

        response = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )

        auth_token = response['AuthenticationResult']['IdToken']

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'User authenticated successfully.', 'idToken': auth_token})
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
