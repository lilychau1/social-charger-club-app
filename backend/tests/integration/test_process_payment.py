import json
import os
import boto3
import unittest
from unittest.mock import patch, MagicMock
import pytest
from botocore.exceptions import ClientError
from lambda_functions.process_payment.app import lambda_handler

def load_env_vars():
    with open('backend/env.json', 'r') as env_file:
        env_vars = json.load(env_file)
        os.environ['PRODUCERS_TABLE_NAME'] = env_vars['ProcessPaymentFunction']['PRODUCERS_TABLE_NAME']
        os.environ['TRANSACTIONS_TABLE_NAME'] = env_vars['ProcessPaymentFunction']['TRANSACTIONS_TABLE_NAME']
        os.environ['CUSTOMER_PAYMENT_INFORMATION_TABLE_NAME'] = env_vars['ProcessPaymentFunction']['CUSTOMER_PAYMENT_INFORMATION_TABLE_NAME']

load_env_vars()

dynamodb = boto3.resource('dynamodb')

mock_producer_id = 'mock-producer-id'
mock_uuid_id = 'mock-uuid-id'
mock_stripe_account_id = 'mock-stripe-account-id'

@pytest.fixture(scope='module')
def dynamodb_table_producers():
    table = dynamodb.Table(os.environ['PRODUCERS_TABLE_NAME'])
    
    table.put_item(
        Item={
            'producerId': mock_producer_id,
            'stripeAccountId': mock_stripe_account_id
        }
    )
    yield table
    table.delete_item(Key={'producerId': mock_producer_id})
    
@pytest.fixture(scope='module')
def dynamodb_table_transactions():
    table = dynamodb.Table(os.environ['TRANSACTIONS_TABLE_NAME'])
    
    yield table
    
    # Clean up test data
    table.delete_item(Key={'transactionId': mock_uuid_id})

mock_payment_info_id_1 = 'mock-payment-info-id-1'
mock_payment_info_id_2 = 'mock-payment-info-id-2'
mock_payment_method_id_1 = 'mock-payment-method-id-1'
mock_payment_method_id_2 = 'mock-payment-method-id-2'
mock_consumer_id = 'mock-consumer-id'

@pytest.fixture(scope='module')
def dynamodb_table_customer_payment_information():

    table = dynamodb.Table(os.environ.get('CUSTOMER_PAYMENT_INFORMATION_TABLE_NAME'))
    test_data = {
        'paymentInfoId': mock_payment_info_id_1, 
        'consumerId': mock_consumer_id, 
        'paymentMethodId': mock_payment_method_id_1, 
        'updateAt': '1999-01-01T00:00:00'
    }
    table.put_item(Item=test_data)
    yield table
    
    table.delete_item(Key={'paymentInfoId': test_data['paymentInfoId']})
    table.delete_item(Key={'paymentInfoId': mock_uuid_id})

@patch('lambda_functions.process_payment.app.get_stripe_account_for_producer')    
@patch('lambda_functions.process_payment.app.stripe.PaymentIntent.create')
@patch('lambda_functions.process_payment.app.stripe.Transfer.create')
@patch('lambda_functions.process_payment.app.uuid')
def test_lambda_handler_successful_payment(
    mock_uuid, 
    mock_transfer_create, 
    mock_payment_intent_create, 
    mock_get_stripe_function, 
    dynamodb_table_producers, 
    dynamodb_table_transactions, 
    dynamodb_table_customer_payment_information
):
    # Mock Stripe API responses
    mock_payment_intent = MagicMock(id="pi_12345")
    mock_transfer = MagicMock(id="tr_12345")
    mock_payment_intent_create.return_value = mock_payment_intent
    mock_transfer_create.return_value = mock_transfer

    mock_uuid.uuid4.return_value = mock_uuid_id

    mock_get_stripe_function.return_value = mock_stripe_account_id
    
    # Define event for the Lambda function
    event = {
        'httpMethod': 'POST', 
        'body': json.dumps({
            'paymentMethodId': mock_payment_info_id_2,
            'amount': 5000,
            'consumerId': mock_consumer_id,
            'producerId': mock_producer_id,
            'chargingPointId': 'test-charging-point',
            'oocpChargePointId': 'test-oocp-id'
        })
    }
    
    # Call Lambda handler function
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert 'message' in response_body
    assert response_body['message'] == 'Payment processed successfully'

    mock_payment_intent_create.assert_called_once_with(
        amount=5000,
        currency='usd',
        payment_method=mock_payment_info_id_2,
        confirmation_method='manual',
        confirm=True,
        transfer_group='mock-stripe-account-id'
    )
    mock_transfer_create.assert_called_once_with(
        amount=5000,
        currency='usd',
        destination='mock-stripe-account-id',
        transfer_group=mock_payment_intent.transfer_group
    )

    response = dynamodb.Table(os.environ['TRANSACTIONS_TABLE_NAME']).scan()
    assert any(item['consumerId'] == mock_consumer_id for item in response.get('Items', []))

    response = dynamodb.Table(os.environ['CUSTOMER_PAYMENT_INFORMATION_TABLE_NAME']).get_item(Key={'paymentInfoId': mock_uuid_id})

    assert response.get('Item') is not None
    assert response['Item']['paymentMethodId'] == mock_payment_info_id_2

@patch('lambda_functions.process_payment.app.get_stripe_account_for_producer')    
@patch('lambda_functions.process_payment.app.stripe.PaymentIntent.create')
@patch('lambda_functions.process_payment.app.stripe.Transfer.create')
@patch('lambda_functions.process_payment.app.uuid')
@patch('lambda_functions.process_payment.app.store_payment_method')
def test_lambda_handler_existing_payment_method(
    mock_store_payment_method_function, 
    mock_uuid, 
    mock_transfer_create, 
    mock_payment_intent_create, 
    mock_get_stripe_function, 
    dynamodb_table_producers, 
    dynamodb_table_transactions, 
    dynamodb_table_customer_payment_information
):
    mock_payment_intent = MagicMock(id="pi_12345")
    mock_transfer = MagicMock(id="tr_12345")
    mock_payment_intent_create.return_value = mock_payment_intent
    mock_transfer_create.return_value = mock_transfer

    mock_uuid.uuid4.return_value = mock_uuid_id

    mock_get_stripe_function.return_value = mock_stripe_account_id
    
    event = {
        'httpMethod': 'POST', 
        'body': json.dumps({
            'paymentMethodId': mock_payment_method_id_1, 
            'amount': 5000,
            'consumerId': mock_consumer_id,
            'producerId': mock_producer_id,
            'chargingPointId': 'test-charging-point',
            'oocpChargePointId': 'test-oocp-id'
        })
    }
    
    # Call Lambda handler function
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert 'message' in response_body
    assert response_body['message'] == 'Payment processed successfully'

    mock_payment_intent_create.assert_called_once_with(
        amount=5000,
        currency='usd',
        payment_method=mock_payment_method_id_1,
        confirmation_method='manual',
        confirm=True,
        transfer_group='mock-stripe-account-id'
    )
    mock_transfer_create.assert_called_once_with(
        amount=5000,
        currency='usd',
        destination='mock-stripe-account-id',
        transfer_group=mock_payment_intent.transfer_group
    )
    mock_store_payment_method_function.assert_not_called()

@patch('lambda_functions.process_payment.app.get_stripe_account_for_producer')
@patch('lambda_functions.process_payment.app.stripe.PaymentIntent.create')
@patch('lambda_functions.process_payment.app.stripe.Transfer.create')
def test_lambda_handler_missing_parameters(mock_transfer_create, mock_payment_intent_create, mock_get_stripe_function):
    mock_get_stripe_function.return_value = mock_stripe_account_id

    event = {
        'httpMethod': 'POST', 
        'body': json.dumps({
            'amount': 5000,
            'consumerId': 'test-consumer',
            # Missing 'payment_method', 'producerId', 'chargingPointId', 'oocpChargePointId'
        })
   }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 400
    response_body = json.loads(response['body'])
    assert 'error' in response_body
    assert response_body['error'] == 'Missing required parameters'

    mock_payment_intent_create.assert_not_called()
    mock_transfer_create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
