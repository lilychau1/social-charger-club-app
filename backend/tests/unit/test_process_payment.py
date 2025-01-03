import unittest
from unittest.mock import patch, MagicMock
import json
from lambda_functions.process_payment.app import lambda_handler, get_stripe_account_for_producer, log_payment_to_dynamodb


class TestLambdaFunction(unittest.TestCase):
        
    @patch('lambda_functions.process_payment.app.stripe.PaymentIntent.create')
    @patch('lambda_functions.process_payment.app.stripe.Transfer.create')
    @patch('lambda_functions.process_payment.app.transactions_table')
    @patch('lambda_functions.process_payment.app.producers_table')
    def test_lambda_handler_successful_payment(self, mock_producers_table, mock_transactions_table, mock_payment_intent_create, mock_transfer_create):
        mock_producers_table.get_item.return_value = {
            'Item': {
                'stripeAccountId': 'mock-stripe-account-id',
                'other-field': 'some-data', 
            }
        }
        
        mock_transactions_table.put_item.return_value = 'Updated'
        
        mock_payment_intent_create.return_value = MagicMock(id="pi_12345")
        mock_transfer_create.return_value = MagicMock(id="tr_12345")

        event = {
            'payment_method': 'pm_card_visa',
            'amount': 1000,
            'consumerId': 'consumer123',
            'producerId': 'producer123',
            'chargingPointId': 'cp123',
            'oocpChargePointId': 'oocp123'
        }

        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Payment processed successfully')
        self.assertIn('payment_intent', body)
        self.assertIn('transfer', body)

        # Verify the payment record in DynamoDB
        mock_transactions_table.put_item.assert_called_once()
        put_item_call_args = mock_transactions_table.put_item.call_args[1]['Item']
        self.assertEqual(put_item_call_args['consumerId'], 'consumer123')
        self.assertEqual(put_item_call_args['producerId'], 'producer123')
        self.assertTrue(put_item_call_args['isSuccessful'])

    @patch('lambda_functions.process_payment.app.transactions_table')
    def test_lambda_handler_missing_parameters(self, mock_transactions_table):
        event = {
            'payment_method': 'pm_card_visa',
            'amount': 1000,
            'consumerId': 'consumer123',
            # Missing 'producerId' and other required fields
        }

        context = {}
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('error', body)
        self.assertEqual(body['error'], 'Missing required parameters')

        mock_transactions_table.put_item.assert_called_once()

    @patch('lambda_functions.process_payment.app.transactions_table')
    @patch('lambda_functions.process_payment.app.producers_table')
    def test_lambda_handler_invalid_producer(self, mock_producers_table, mock_transactions_table):
        mock_producers_table.get_item.return_value = {}
        mock_transactions_table.put_item.return_value = 'Updated'
        
        event = {
            'payment_method': 'pm_card_visa',
            'amount': 1000,
            'consumerId': 'consumer123',
            'producerId': 'invalidProducer',
            'chargingPointId': 'cp123',
            'oocpChargePointId': 'oocp123'
        }

        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('error', body)
        self.assertIn('does not have a valid Stripe account', body['error'])

        mock_transactions_table.put_item.assert_called_once()

    @patch('lambda_functions.process_payment.app.producers_table')
    def test_get_stripe_account_for_producer(self, mock_producers_table):
        mock_producers_table.get_item.return_value = {
            'Item': {
                'stripeAccountId': 'mock-stripe-account-id',
                'other-field': 'some-data', 
            }
        }
        producer_id = 'producer123'
        stripe_account_id = get_stripe_account_for_producer(producer_id)
        self.assertEqual(stripe_account_id, 'mock-stripe-account-id')

        # Update mock to simulate producer not found
        mock_producers_table.get_item.return_value = {}

        invalid_producer_id = 'invalidProducer'
        stripe_account_id = get_stripe_account_for_producer(invalid_producer_id)
        self.assertIsNone(stripe_account_id)

    @patch('lambda_functions.process_payment.app.transactions_table')
    def test_log_payment_to_dynamodb(self, mock_transactions_table):
        mock_transactions_table.put_item.return_value = 'Updated'
        
        log_payment_to_dynamodb(
            consumer_id='consumer123',
            producer_id='producer123',
            charging_point_id='cp123',
            oocp_charge_point_id='oocp123',
            amount=1000,
            payment_method='pm_card_visa',
            is_successful=True,
            message='Test payment success'
        )

        mock_transactions_table.put_item.assert_called_once()
        args, kwargs = mock_transactions_table.put_item.call_args
        item = kwargs['Item']
        self.assertEqual(item['consumerId'], 'consumer123')
        self.assertEqual(item['producerId'], 'producer123')
        self.assertTrue(item['isSuccessful'])

if __name__ == '__main__':
    unittest.main()
