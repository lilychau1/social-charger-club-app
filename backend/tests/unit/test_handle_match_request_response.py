import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from lambda_functions.handle_match_request_response.app import lambda_handler, get_user_email, send_email_notification_to_sender


class TestLambdaFunction(unittest.TestCase):
    @patch('lambda_functions.handle_match_request_response.app.match_requests_table')
    @patch('lambda_functions.handle_match_request_response.app.users_table')
    @patch('lambda_functions.handle_match_request_response.app.ses_client')
    @patch('lambda_functions.handle_match_request_response.app.ssm_client')
    def test_lambda_handler_success(self, mock_ssm_client, mock_ses_client, mock_users_table, mock_match_requests_table):
        mock_ssm_client.get_parameter.return_value = {
            'Parameter': {'Value': 'mock-ses-email@example.com'}
        }
        mock_users_table.query.return_value = {
            'Items': [{'email': 'sender@example.com'}]
        }
        mock_match_requests_table.update_item.return_value = {}

        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'requestId': 'mock-request-id',
                'senderConsumerId': 'mock-sender-id',
                'recipientConsumerId': 'mock-recipient-id',
                'requestResponse': 'Accept'
            })
        }
        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['message'], 'Match request response sent successfully')

        mock_match_requests_table.update_item.assert_called_once()
        mock_ses_client.send_email.assert_called_once()

    @patch('lambda_functions.handle_match_request_response.app.match_requests_table')
    def test_lambda_handler_missing_parameters(self, mock_match_requests_table):
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'senderConsumerId': 'mock-sender-id',
                # Missing 'requestId', 'recipientConsumerId', 'requestResponse'
            })
        }
        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Missing required fields in request body')
        mock_match_requests_table.update_item.assert_not_called()

    @patch('lambda_functions.handle_match_request_response.app.users_table')
    @patch('lambda_functions.handle_match_request_response.app.ses_client')
    def test_lambda_handler_user_not_found(self, mock_ses_client, mock_users_table):
        mock_users_table.query.return_value = {'Items': []}

        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'requestId': 'mock-request-id',
                'senderConsumerId': 'mock-sender-id',
                'recipientConsumerId': 'mock-recipient-id',
                'requestResponse': 'Accept'
            })
        }
        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertEqual(body['error'], 'Sender user not found')
        mock_ses_client.send_email.assert_not_called()

    @patch('lambda_functions.handle_match_request_response.app.users_table')
    @patch('lambda_functions.handle_match_request_response.app.ses_client')
    def test_lambda_handler_ses_failure(self, mock_ses_client, mock_users_table):
        mock_users_table.query.return_value = {'Items': [{'email': 'sender@example.com'}]}
        
        mock_ses_client.send_email.side_effect = Exception("SES failed to send email")

        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'requestId': 'mock-request-id',
                'senderConsumerId': 'mock-sender-id',
                'recipientConsumerId': 'mock-recipient-id',
                'requestResponse': 'Accept'
            })
        }
        context = {}
        response = lambda_handler(event, context)

        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertIn('SES failed to send email', body['error'])

    @patch('lambda_functions.handle_match_request_response.app.users_table')
    def test_get_user_email(self, mock_users_table):
        mock_users_table.query.return_value = {
            'Items': [{'email': 'test@example.com'}]
        }
        email = get_user_email('mock-consumer-id')
        self.assertEqual(email, 'test@example.com')

        mock_users_table.query.return_value = {'Items': []}
        email = get_user_email('nonexistent-id')
        self.assertIsNone(email)

    @patch('lambda_functions.handle_match_request_response.app.ses_client')
    def test_send_email_notification_to_sender(self, mock_ses_client):
        send_email_notification_to_sender(
            ses_email='mock-ses@example.com',
            sender_email='sender@example.com',
            recipient_consumer_id='mock-recipient-id'
        )
        mock_ses_client.send_email.assert_called_once()
        args, kwargs = mock_ses_client.send_email.call_args
        self.assertEqual(kwargs['Destination']['ToAddresses'], ['sender@example.com'])
        self.assertIn('mock-recipient-id', kwargs['Message']['Body']['Text']['Data'])


if __name__ == '__main__':
    unittest.main()
