import json
import boto3
import os
from botocore.exceptions import ClientError

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

        if not email:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing email.'})
            }

        # Resend the confirmation code to the user
        response = cognito.resend_confirmation_code(
            ClientId=client_id,
            Username=email
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Confirmation code resent successfully.', 'response': response})
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
