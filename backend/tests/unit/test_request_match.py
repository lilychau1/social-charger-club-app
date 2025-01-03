import unittest
from unittest.mock import patch, MagicMock, ANY
import json
import os
from request_match.app import lambda_handler, get_ssm_parameter

class TestMatchRequestLambdaFunction(unittest.TestCase):
    
    @patch('request_match.app.match_requests_table')
    @patch('request_match.app.users_table')
    @patch('request_match.app.ses_client')
    @patch('request_match.app.ssm_client')
    def test_lambda_handler_success(self, mock_ssm_client, mock_ses_client, mock_users_table, mock_match_requests_table):
        mock_email_domain = 'mock-email-domain'
        mock_recipient_email = f'recipient@{mock_email_domain}.com'
        mock_ses_email = f'no-reply@{mock_email_domain}.com'
        
        mock_users_table.query.return_value = {
            'Items': [{'email': mock_recipient_email}]
        }

        mock_ssm_client.get_parameter.return_value = {'Parameter': {'Value': mock_ses_email}}

        # Define the input event
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'senderConsumerId': '123',
                'recipientConsumerId': '456',
                'meetingStartTime': '2025-01-01T10:00:00Z',
                'meetingEndTime': '2025-01-01T11:00:00Z',
                'matchEventType': 'Coffee & Chat'
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['message'], 'Match request sent successfully')

        mock_match_requests_table.put_item.assert_called_once()

        mock_users_table.query.assert_called_once_with(
            IndexName='consumerIdEmailIndex',
            KeyConditionExpression=ANY
        )

        mock_ses_client.send_email.assert_called_once_with(
            Source=mock_ses_email,
            Destination={'ToAddresses': [mock_recipient_email]},
            Message={
                'Subject': {'Data': ANY},
                'Body': {'Text': {'Data': ANY}}
            }
        )

    @patch('request_match.app.match_requests_table')
    @patch('request_match.app.users_table')
    @patch('request_match.app.ses_client')
    @patch('request_match.app.ssm_client')
    def test_lambda_handler_missing_fields(self, mock_ssm_client, mock_ses_client, mock_users_table, mock_match_requests_table):
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'senderConsumerId': '123',
                'meetingStartTime': '2025-01-01T10:00:00Z',
                'meetingEndTime': '2025-01-01T11:00:00Z'
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        response_body = json.loads(response['body'])
        self.assertIn('error', response_body)
        self.assertEqual(response_body['error'], 'Missing required fields in request body')

    @patch('request_match.app.ssm_client')
    def test_get_ssm_parameter(self, mock_ssm_client):

        mock_param_key = 'mock-param-key'
        mock_param_value = 'mock-param-value'
    
        mock_ssm_client.get_parameter.return_value = {
            'Parameter': {
                'Name': mock_param_key, 
                'Value': mock_param_value
            }
        }
        
        
        result = get_ssm_parameter(mock_param_key)
        
        # Assertions
        self.assertEqual(result, mock_param_value)
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name=mock_param_key, WithDecryption=True
        )

    def test_lambda_handler_options_method(self):
        event = {
            'httpMethod': 'OPTIONS',
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])

if __name__ == '__main__':
    unittest.main()
