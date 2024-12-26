import json
import boto3
import os
from botocore.exceptions import ClientError

dynamodb = boto3.client('dynamodb')

options_headers = {
    'Access-Control-Allow-Origin': 'http://localhost:3000', 
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

def build_update_expression(updates):
    update_expressions = []
    expression_attribute_names = {}
    expression_attribute_values = {}

    for idx, (key, value) in enumerate(updates.items()):
        update_expressions.append(f"#key{idx} = :val{idx}")
        expression_attribute_names[f"#key{idx}"] = key
        expression_attribute_values[f":val{idx}"] = {'S': value}

    return {
        "UpdateExpression": "SET " + ", ".join(update_expressions),
        "ExpressionAttributeNames": expression_attribute_names,
        "ExpressionAttributeValues": expression_attribute_values
    }

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {
            "statusCode": 200,
            'headers': options_headers,
            "body": json.dumps({})
        }

    try:
        print("Received event: ", json.dumps(event))
        
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("userId")
        consumer_id = body.get("consumerId")
        producer_id = body.get("producerId")
        updates = body.get("updates", {})

        # Validate input
        if not user_id or not updates:
            return {
                "statusCode": 400,
                'headers': options_headers,
                "body": json.dumps({"error": "Invalid input. userId and updates are required."})
            }

        user_table = os.environ.get('USERS_TABLE_NAME')
        consumer_table = os.environ.get('CONSUMERS_TABLE_NAME')
        producer_table = os.environ.get('PRODUCERS_TABLE_NAME')

        logs = []

        # Update User Table
        if 'basic' in updates:
            user_update = updates['basic']
            expressions = build_update_expression(user_update)

            dynamodb.update_item(
                TableName=user_table,
                Key={'userId': {'S': user_id}},
                **expressions
            )

            logs.append(f"Updated user data for {user_id} in {user_table}: {user_update}")

        # Update Consumer Table
        if 'consumer' in updates and consumer_id:
            consumer_update = updates['consumer']
            expressions = build_update_expression(consumer_update)

            dynamodb.update_item(
                TableName=consumer_table,
                Key={'consumerId': {'S': consumer_id}},
                **expressions
            )

            logs.append(f"Updated consumer data for {consumer_id} in {consumer_table}: {consumer_update}")

        # Update Producer Table
        if 'producer' in updates and producer_id:
            producer_update = updates['producer']
            expressions = build_update_expression(producer_update)

            dynamodb.update_item(
                TableName=producer_table,
                Key={'producerId': {'S': producer_id}},
                **expressions
            )

            logs.append(f"Updated producer data for {producer_id} in {producer_table}: {producer_update}")

        # Log all updates
        for log in logs:
            print(log)

        return {
            "statusCode": 200,
            'headers': options_headers,
            "body": json.dumps({"message": "User details updated successfully"})
        }

    except ClientError as e:
        print(f"ClientError: {e}")
        return {
            "statusCode": 500,
            'headers': options_headers,
            "body": json.dumps({"error": f"Client error: {e.response['Error']['Message']}"})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            'headers': options_headers,
            "body": json.dumps({"error": f"Server error: {str(e)}"})
        }
