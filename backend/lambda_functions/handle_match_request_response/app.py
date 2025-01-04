import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
ses_client = boto3.client('ses')
ssm_client = boto3.client('ssm')

match_requests_table = dynamodb.Table(os.environ.get('MATCH_REQUESTS_TABLE_NAME'))
users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME'))

cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def get_ssm_parameter(param_name):
    try:
        value = os.environ.get('SES_EMAIL')
        if value: 
            return value
        response = ssm_client.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except ClientError as e:
        print(f"Error fetching {param_name} from SSM: {str(e)}")
        return None

PARAMETER_PREFIX = os.environ.get('PARAMETER_PREFIX')

def lambda_handler(event, context):

    # Handle CORS preflight requests (OPTIONS)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_header
        }

    try:
        ses_email = get_ssm_parameter(PARAMETER_PREFIX + 'SES_EMAIL')
        body = json.loads(event['body'])

        request_id = body.get('requestId')
        sender_consumer_id = body.get('senderConsumerId')
        recipient_consumer_id = body.get('recipientConsumerId')
        request_response = body.get('requestResponse')
        
        if not sender_consumer_id or not recipient_consumer_id or not request_id or not request_response:
            return {
                'statusCode': 400,
                'headers': cors_header, 
                'body': json.dumps({'error': 'Missing required fields in request body'})
            }

        timestamp = datetime.now().isoformat()
        
        # 'Accepted' or 'Rejected'
        match_status = f'{request_response}ed'

        # Update requests table
        match_requests_table.update_item(
            Key={'requestId': request_id},
            UpdateExpression=(
                'SET matchStatus = :match_status, '
                'statusUpdatedAt = :timestamp'
            ),
            ExpressionAttributeValues={
                ':match_status': match_status,
                ':timestamp': timestamp
            }
        )

        # Send email to sender for outcome
        sender_email = get_user_email(sender_consumer_id)
        if not sender_email:
            return {
                'statusCode': 404,
                'headers': cors_header,
                'body': json.dumps({'error': 'Sender user not found'})
            }

        send_email_notification_to_sender(
            ses_email, 
            sender_email,
            recipient_consumer_id
        )
        
        return {
            'statusCode': 200,
            'headers': cors_header,
            'body': json.dumps({'message': 'Match request response sent successfully'})
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_header,
            'body': json.dumps({'error': str(e)})
        }

def get_user_email(consumer_id):
    try:
        response = users_table.query(
            IndexName='consumerIdEmailIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('consumerId').eq(consumer_id)
        )   
        items = response.get('Items', [])
        if items:
            return items[0].get('email')
        else:
            return None    
         
    except ClientError as e:
        print(f"Error fetching user email: {e.response['Error']['Message']}")
        return None

def send_email_notification_to_sender(ses_email, sender_email, recipient_consumer_id):
    try:
        subject = "Someone responded to your match request!"
        body = (
            f"Hello,\n\n"
            f"You've received a response to your match request from user {recipient_consumer_id}.\n\n"
            f"Please log in to your account to view the outcome.\n\n"
            f"Thank you!"
        )

        ses_client.send_email(
            Source=ses_email,
            Destination={'ToAddresses': [sender_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        raise