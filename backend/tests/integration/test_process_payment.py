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

load_env_vars()

dynamodb = boto3.resource('dynamodb')

mock_producer_id = 'mock-producer-id'
mock_transaction_id = 'mock-transaction-id'
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
    table.delete_item(Key={'producerId': mock_producer_id})

    yield table
    
@pytest.fixture(scope='module')
def dynamodb_table_transactions():
    table = dynamodb.Table(os.environ['TRANSACTIONS_TABLE_NAME'])
    
    yield table
    
    # Clean up test data
    table.delete_item(Key={'transactionId': mock_transaction_id})

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
    dynamodb_table_transactions
):
    # Mock Stripe API responses
    mock_payment_intent = MagicMock(id="pi_12345")
    mock_transfer = MagicMock(id="tr_12345")
    mock_payment_intent_create.return_value = mock_payment_intent
    mock_transfer_create.return_value = mock_transfer

    mock_uuid.uuid4.return_value = mock_transaction_id

    mock_get_stripe_function.return_value = mock_stripe_account_id
    
    # Define event for the Lambda function
    event = {
        'payment_method': 'pm_12345',
        'amount': 5000,  # $50.00 in cents
        'consumerId': 'mock-customer-id',
        'producerId': mock_producer_id,
        'chargingPointId': 'test-charging-point',
        'oocpChargePointId': 'test-oocp-id'
    }

    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert 'message' in response_body
    assert response_body['message'] == 'Payment processed successfully'

    mock_payment_intent_create.assert_called_once_with(
        amount=5000,
        currency='usd',
        payment_method='pm_12345',
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

    # Verify DynamoDB transactions table was updated
    response = dynamodb.Table(os.environ['TRANSACTIONS_TABLE_NAME']).scan()
    assert any(item['consumerId'] == 'mock-customer-id' for item in response.get('Items', []))

@patch('lambda_functions.process_payment.app.get_stripe_account_for_producer')
@patch('lambda_functions.process_payment.app.stripe.PaymentIntent.create')
@patch('lambda_functions.process_payment.app.stripe.Transfer.create')
def test_lambda_handler_missing_parameters(mock_transfer_create, mock_payment_intent_create, mock_get_stripe_function):
    mock_get_stripe_function.return_value = mock_stripe_account_id

    event = {
        'amount': 5000,
        'consumerId': 'test-consumer',
        # Missing 'payment_method', 'producerId', 'chargingPointId', 'oocpChargePointId'
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
