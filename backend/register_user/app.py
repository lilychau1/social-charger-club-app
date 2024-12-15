import json
import boto3
import uuid
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = 'EVCharging_Users'
table = dynamodb.Table(table_name)

cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def generate_ids():
    # Generate UUIDs for user_id, consumer_id, and producer_id
    return str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

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
        username = body.get('username', email)
        user_type = body.get('user_type')

        # Generate IDs
        user_id, consumer_id, producer_id = generate_ids()

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
