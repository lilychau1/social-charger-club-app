import json
import os
import stripe
import boto3
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
secrets_clientr = boto3.client('secretsmanager')
producers_table = dynamodb.Table(os.environ.get('PRODUCERS_TABLE_NAME'))
transactions_table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE_NAME'))

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

def lambda_handler(event, context):
    try:
        user_payment_method = event.get('payment_method')
        amount = event.get('amount')
        consumer_id = event.get('consumerId')
        producer_id = event.get('producerId')
        charging_point_id = event.get('chargingPointId')
        oocp_charge_point_id = event.get('oocpChargePointId')

        if not all([user_payment_method, amount, consumer_id, producer_id, charging_point_id, oocp_charge_point_id]):
            error_message = 'Missing required parameters'
            log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, user_payment_method, False, error_message)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_message})
            }

        producer_stripe_account_id = get_stripe_account_for_producer(producer_id)

        if not producer_stripe_account_id:
            error_message = f"Producer {producer_id} does not have a valid Stripe account"
            log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, user_payment_method, False, error_message)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_message})
            }

        payment_intent = stripe.PaymentIntent.create(
            amount=amount, 
            currency='usd', 
            payment_method=user_payment_method, 
            confirmation_method='manual',
            confirm=True,
            transfer_group=producer_stripe_account_id,
        )

        transfer = stripe.Transfer.create(
            amount=amount, 
            currency='usd',
            destination=producer_stripe_account_id,
            transfer_group=payment_intent.transfer_group,
        )

        success_message = 'Payment processed successfully'
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, user_payment_method, True, success_message)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': success_message,
                'payment_intent': payment_intent.id,
                'transfer': transfer.id
            })
        }

    except stripe.error.StripeError as e:
        error_message = f"Stripe error: {str(e)}"
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, user_payment_method, False, error_message)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_message})
        }
    except Exception as e:
        error_message = f"Internal error: {str(e)}"
        log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, user_payment_method, False, error_message)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }

def get_stripe_account_for_producer(producer_id):
    try:
        response = producers_table.get_item(Key={'producerId': producer_id})
        if 'Item' in response and 'stripeAccountId' in response['Item']:
            return response['Item']['stripeAccountId']
        return None
    except ClientError as e:
        print(f"Error fetching Stripe account ID for producer {producer_id}: {str(e)}")
        return None

def log_payment_to_dynamodb(consumer_id, producer_id, charging_point_id, oocp_charge_point_id, amount, payment_method, is_successful, message):
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
            'userPaymentMethod': payment_method,
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
