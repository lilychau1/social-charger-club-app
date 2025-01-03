import json
import uuid
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

        sender_consumer_id = body.get('senderConsumerId')
        recipient_consumer_id = body.get('recipientConsumerId')
        meeting_start_time = body.get('meetingStartTime')
        meeting_end_time = body.get('meetingEndTime')
        match_event_type = body.get('matchEventType', 'Other')
        
        if not sender_consumer_id or not recipient_consumer_id or not meeting_start_time or not meeting_end_time:
            return {
                'statusCode': 400,
                'headers': cors_header, 
                'body': json.dumps({'error': 'Missing required fields in request body'})
            }
        
        match_request_id = str(uuid.uuid4())

        timestamp = datetime.now().isoformat()
        match_requests_table.put_item(
            Item={
                'requestId': match_request_id,
                'senderConsumerId': sender_consumer_id,
                'recipientConsumerId': recipient_consumer_id,
                'timestamp': timestamp,
                'startTime#endTime': f'{meeting_start_time}#{meeting_end_time}',
                'matchStatus': 'Pending',
                'matchEventType': match_event_type,
                'isRead': int(False)
            }
        )
        
        recipient_email = get_user_email(recipient_consumer_id)
        if not recipient_email:
            return {
                'statusCode': 404,
                'headers': cors_header,
                'body': json.dumps({'error': 'Recipient user not found'})
            }

        send_email_notification(
            ses_email, 
            recipient_email,
            sender_consumer_id,
            match_event_type,
            meeting_start_time,
            meeting_end_time
        )
        
        return {
            'statusCode': 200,
            'headers': cors_header,
            'body': json.dumps({'message': 'Match request sent successfully'})
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

def send_email_notification(ses_email, recipient_email, sender_consumer_id, event_type, start_time, end_time):
    try:
        subject = "You've received a new match request!"
        body = (
            f"Hello,\n\n"
            f"You've received a new match request from user {sender_consumer_id}.\n\n"
            f"Event Type: {event_type}\n"
            f"Start Time: {start_time}\n"
            f"End Time: {end_time}\n\n"
            f"Please log in to your account to accept or reject this request.\n\n"
            f"Thank you!"
        )

        ses_client.send_email(
            Source=ses_email,
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        raise
