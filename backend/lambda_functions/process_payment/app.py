import json
import os
import stripe
import boto3
from boto3.dynamodb.conditions import Key
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize DynamoDB resource and Secrets Manager
dynamodb = boto3.resource('dynamodb')
secrets_clientr = boto3.client('secretsmanager')

producers_table = dynamodb.Table(os.environ.get('PRODUCERS_TABLE_NAME'))
transactions_table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE_NAME'))
customer_payment_info_table = dynamodb.Table(os.environ.get('CUSTOMER_PAYMENT_INFORMATION_TABLE_NAME'))

# CORS headers
cors_header = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Api-Key, X-Amz-Security-Token'
}

# Function to fetch the Stripe API key
def get_stripe_api_key():
    api_key = os.environ.get('STRIPE_API_KEY')
    if api_key: 
        return api_key

    try:
        response = secrets_clientr.get_secret_value(SecretId=os.environ.get('SECRET_NAME'))
        secret = json.loads(response['SecretString'])
        return secret['STRIPE_API_KEY']
    except ClientError as e:
        print(f"Error fetching Stripe API key from Secrets Manager: {str(e)}")
        raise Exception("Stripe API key not found.")
    except KeyError:
        print("STRIPE_API_KEY not found in Secrets Manager's response.")
        raise Exception("Stripe API key not found in the secret.")


stripe.api_key = get_stripe_api_key()

# Main Lambda handler function
def lambda_handler(event, context):
    # Handle CORS preflight requests (OPTIONS)
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_header
        }

    try:
        event_body = json.loads(event.get('body'))

        # Extract data from event body
        payment_method_id = event_body.get('paymentMethodId')
        amount = event_body.get('amount')
        consumer_id = event_body.get('consumerId')
        producer_id = event_body.get('producerId')
        charging_point_id = event_body.get('chargingPointId')
        oocp_charge_point_id = event_body.get('oocpChargePointId')

        if not all([payment_method_id, amount, consumer_id, producer_id, charging_point_id, oocp_charge_point_id]):
            error_message = 'Missing required parameters'
            log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method_id, False, error_message)
            return {
                'statusCode': 400,
                'headers': cors_header, 
                'body': json.dumps({'error': error_message})
            }

        # Get the Stripe account ID for the producer
        producer_stripe_account_id = get_stripe_account_for_producer(producer_id)

        if not producer_stripe_account_id:
            error_message = f"Producer {producer_id} does not have a valid Stripe account"
            log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method_id, False, error_message)
            return {
                'statusCode': 400,
                'headers': cors_header, 
                'body': json.dumps({'error': error_message})
            }

        # Create a PaymentIntent in Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=amount, 
            currency='usd', 
            payment_method=payment_method_id, 
            confirmation_method='manual',
            confirm=True,
            transfer_group=producer_stripe_account_id,
        )

        # Create a Transfer to the producer's Stripe account
        transfer = stripe.Transfer.create(
            amount=amount, 
            currency='usd',
            destination=producer_stripe_account_id,
            transfer_group=payment_intent.transfer_group,
        )
        
        # Check if the payment method exists for the customer
        payment_method_exists = check_payment_method_exists(consumer_id, payment_method_id)

        if not payment_method_exists:
            store_payment_method(consumer_id, payment_method_id)

        success_message = 'Payment processed successfully'
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method_id, True, success_message)

        return {
            'statusCode': 200,
            'headers': cors_header, 
            'body': json.dumps({
                'message': success_message,
                'payment_intent': payment_intent.id,
                'transfer': transfer.id
            })
        }
    except stripe.error.StripeError as e:
        error_message = f"Stripe error: {str(e)}"
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method_id, False, error_message)
        return {
            'statusCode': 400,
            'headers': cors_header, 
            'body': json.dumps({'error': error_message})
        }
    except Exception as e:
        breakpoint()
        error_message = f"Internal error: {str(e)}"
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method_id, False, error_message)
        return {
            'statusCode': 500,
            'headers': cors_header, 
            'body': json.dumps({'error': error_message})
        }

def check_payment_method_exists(consumer_id, payment_method_id):
    try:
        response = customer_payment_info_table.query(
            IndexName='consumerIdIndex',
            KeyConditionExpression=Key('consumerId').eq(consumer_id)  # Query for a specific consumerId
        )

        if 'Items' in response:
            item = response['Items'][0]
            if 'paymentMethodId' in item:
                return item['paymentMethodId'] == payment_method_id
        return False
    
    except ClientError as e:
        print(f"Error checking payment method in DynamoDB: {str(e)}")
        raise Exception(f"Error message: {e}")

def store_payment_method(consumer_id, payment_method_id):
    try:
        payment_info_id = str(uuid.uuid4())
        customer_payment_info_table.put_item(
            Item={
                'paymentInfoId': payment_info_id, 
                'consumerId': consumer_id,
                'paymentMethodId': payment_method_id,
                'updatedAt': datetime.now().isoformat()
            }
        )
    except ClientError as e:
        print(f"Error storing payment method in DynamoDB: {str(e)}")
        raise Exception(f"Error message: {e}")

def get_stripe_account_for_producer(producer_id):
    try:
        response = producers_table.get_item(Key={'producerId': producer_id})
        if 'Item' in response and 'stripeAccountId' in response['Item']:
            return response['Item']['stripeAccountId']
        return None
    except ClientError as e:
        print(f"Error fetching Stripe account ID for producer {producer_id}: {str(e)}")
        return None

def log_payment_to_dynamodb(
    consumer_id, 
    producer_id, 
    charging_point_id, 
    oocp_charge_point_id, 
    amount, 
    payment_method_id, 
    is_successful, 
    message
):
    try:
        transaction_id = str(uuid.uuid4())

        consumer_id_with_is_successful = f"{consumer_id}#{is_successful}"
        producer_id_with_is_successful = f"{producer_id}#{is_successful}"
        charging_point_id_with_is_successful = f"{charging_point_id}#{is_successful}"

        payment_record = {
            'transactionId': transaction_id,
            'consumerId': consumer_id,
            'producerId': producer_id,
            'chargingPointId': charging_point_id,
            'oocpChargePointId': oocp_charge_point_id,
            'paymentMethodId': payment_method_id,
            'amount': amount,
            'isSuccessful': is_successful,
            'timestamp': datetime.now().isoformat(),
            'message': message, 
            'consumerIdWithIsSuccessful': consumer_id_with_is_successful,
            'producerIdWithIsSuccessful': producer_id_with_is_successful,
            'chargingPointIdWithIsSuccessful': charging_point_id_with_is_successful
        }

        transactions_table.put_item(Item=payment_record)

    except ClientError as e:
        print(f"Error logging payment to DynamoDB: {str(e)}")
