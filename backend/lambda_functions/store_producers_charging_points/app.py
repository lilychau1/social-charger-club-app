import json
import boto3
import os
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

dynamodb = boto3.client('dynamodb')

cors_headers = {
    'Access-Control-Allow-Origin': 'http://localhost:3000', 
    'Access-Control-Allow-Methods': 'OPTIONS, POST',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}
def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return {
            "statusCode": 200,
            'headers': cors_headers,
            "body": json.dumps({})
        }

    try:
        print("Received event: ", json.dumps(event))
        
        body = event.get("body")
        if body is None:
            return {
                "statusCode": 400,
                'headers': cors_headers,
                "body": json.dumps({"error": "Invalid input. producerId and chargingPoints are required."})
            }
        
        body = json.loads(body)
        producer_id = body.get("producerId")
        charging_points = body.get("chargingPoints", [])

        # Validate input
        if not producer_id or not charging_points:
            return {
                "statusCode": 400,
                'headers': cors_headers,
                "body": json.dumps({"error": "Invalid input. producerId and chargingPoints are required."})
            }

        charging_points_table = os.environ.get('CHARGING_POINTS_TABLE_NAME')
        charging_point_ids = []
        for point in charging_points:
            charging_point_id = str(uuid.uuid4())
            charging_point_ids.append(charging_point_id)
            point['chargingPointId'] = charging_point_id
            point['producerId'] = producer_id
            
            # Combine latitude and longitude into a single location attribute
            latitude = point.get('latitude')
            longitude = point.get('longitude')
            if latitude is None or longitude is None:
                return {
                    "statusCode": 400,
                    'headers': cors_headers,
                    "body": json.dumps({"error": "Both latitude and longitude are required."})
                }
            
            point['location'] = f"{latitude},{longitude}"
            point['created_at'] = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

            item = {k: {'S': str(v)} for k, v in point.items()}

            # Log item being put into DynamoDB
            print(f"Putting item into DynamoDB: {item}")

            dynamodb.put_item(
                TableName=charging_points_table,
                Item=item
            )

            print(f"Added charging point {charging_point_id} for producer {producer_id}")

        return {
            "statusCode": 200,
            'headers': cors_headers,
            "body": json.dumps(
                {
                    "message": "Charging points added successfully", 
                    "chargingPointIds": charging_point_ids
                }
            )
        }

    except ClientError as e:
        print(f"ClientError: {e}")
        return {
            "statusCode": 500,
            'headers': cors_headers,
            "body": json.dumps({"error": f"Client error: {e.response['Error']['Message']}"})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            'headers': cors_headers,
            "body": json.dumps({"error": f"Server error: {str(e)}"})
        }
