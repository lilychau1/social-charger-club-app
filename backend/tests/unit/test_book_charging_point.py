import unittest
from unittest.mock import patch, MagicMock
import os
import json
from book_charging_point.app import lambda_handler, update_dynamodb_status, send_oocp_reservation_request, get_auth, get_parameter_or_secret

class TestBookChargingPoint(unittest.TestCase):
    @patch('book_charging_point.app.api_gateway_client')
    @patch('book_charging_point.app.charging_points_table')
    @patch('book_charging_point.app.get_parameter_or_secret')
    def test_lambda_handler_success(self, mock_get_parameter_or_secret, mock_charging_points_table, mock_api_gateway_client):
        # Mock the secret and parameter retrieval
        mock_get_parameter_or_secret.return_value = 'mocked-secret-value'

        # Mock DynamoDB and API Gateway responses
        mock_charging_points_table.update_item.return_value = 'Updated'
        mock_api_gateway_client.test_invoke_method.return_value = {
            'status': 200,
            'body': json.dumps({'result': 'success'})
        }

        event = {
            'oocpChargePointId': 'test-point-id',
            'system': 'Virta',
            'connectorId': '1',
            'startTime': '2024-12-30T12:00:00',
            'endTime': '2024-12-30T13:00:00'
        }

        # Run handler
        response = lambda_handler(event, None)

        # Assertions
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Slot booked successfully', response['body'])
        mock_charging_points_table.update_item.assert_called_once()

    @patch('book_charging_point.app.charging_points_table')
    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    def test_update_dynamodb_status(self, mock_get_parameter_or_secret, mock_charging_points_table):
        # Mock the secret and parameter retrieval
        mock_get_parameter_or_secret.return_value = 'mocked-secret-value'

        mock_charging_points_table.update_item.return_value = 'Updated'

        update_dynamodb_status('test-point-id', False)

        mock_charging_points_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': 'test-point-id'},
            UpdateExpression="SET isAvailable = :is_available, statusUpdatedAt = :timestamp",
            ExpressionAttributeValues={
                ':is_available': False,
                ':timestamp': unittest.mock.ANY
            },
            ConditionExpression="attribute_exists(oocpChargePointId)"
        )

    @patch('book_charging_point.app.api_gateway_client')
    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    def test_send_oocp_reservation_request_virta(self, mock_get_parameter_or_secret, mock_api_gateway_client):
        # Mock the secret and parameter retrieval
        mock_get_parameter_or_secret.return_value = 'mocked-secret-value'

        # Mock API Gateway response
        mock_api_gateway_client.test_invoke_method.return_value = {
            'status': 200,
            'body': json.dumps({'result': 'success'})
        }

        response = send_oocp_reservation_request(
            'Virta',
            'test-point-id',
            '1',
            '2024-12-30T12:00:00',
            '2024-12-30T13:00:00'
        )

        self.assertEqual(response['status'], 'success')
        mock_api_gateway_client.test_invoke_method.assert_called_once()

    @patch('book_charging_point.app.api_gateway_client')
    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    def test_send_oocp_reservation_request_evbox(self, mock_get_parameter_or_secret, mock_api_gateway_client):
        # Mock the secret and parameter retrieval
        mock_get_parameter_or_secret.return_value = 'mocked-secret-value'

        mock_api_gateway_client.test_invoke_method.return_value = {
            'status': 200,
            'body': json.dumps({'result': 'success'})
        }

        response = send_oocp_reservation_request(
            'EVBox',
            'test-point-id',
            '1',
            '2024-12-30T12:00:00',
            '2024-12-30T13:00:00'
        )

        self.assertEqual(response['status'], 'success')
        mock_api_gateway_client.test_invoke_method.assert_called_once()

    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    def test_get_auth(self, mock_get_parameter_or_secret):
        # Mock the secret retrieval for testing
        os.environ['VIRTA_API_KEY'] = 'mocked-secret-value'
        os.environ['EVBOX_TOKEN'] = 'mocked-secret-value'

        # Mock the get_parameter_or_secret method to return the mock API keys
        mock_get_parameter_or_secret.return_value = 'mocked-secret-value'

        virta_headers = get_auth('Virta')
        evbox_headers = get_auth('EVBox')

        self.assertEqual(virta_headers, {'X-API-Key': 'mocked-secret-value'})
        self.assertEqual(evbox_headers, {'Authorization': 'Bearer mocked-secret-value'})


    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    @patch('book_charging_point.app.get_ssm_parameter')  # Mock SSM parameter call
    @patch('book_charging_point.app.get_secret_value')  # Mock Secrets Manager secret call
    def test_get_parameter_or_secret_env_var_exists(self, mock_get_secret_value, mock_get_ssm_parameter, mock_get_parameter_or_secret):
        # Where environment variable is set
        os.environ['VIRTA_API_KEY'] = 'env-api-key'
        mock_get_ssm_parameter.return_value = None 
        mock_get_secret_value.return_value = None

        value = get_parameter_or_secret('VIRTA_API_KEY')
        self.assertEqual(value, 'env-api-key')
        mock_get_ssm_parameter.assert_not_called() 
        mock_get_secret_value.assert_not_called()
        
    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    @patch('book_charging_point.app.get_ssm_parameter')  # Mock SSM parameter call
    @patch('book_charging_point.app.get_secret_value')  # Mock Secrets Manager secret call
    def test_get_parameter_or_secret_no_env_var_key(self, mock_get_secret_value, mock_get_ssm_parameter, mock_get_parameter_or_secret):

        # Where environment variable is not set
        mock_get_ssm_parameter.return_value = 'some-param'
        mock_get_secret_value.return_value = 'some-secret' 

        value = get_parameter_or_secret('NON_EXISTING_VARIABLE_KEY')
        self.assertEqual(value, 'some-secret')
        mock_get_ssm_parameter.assert_not_called()
        mock_get_secret_value.assert_called_once()
        
    @patch('book_charging_point.app.get_parameter_or_secret')  # Mock the call to Parameter Store and Secrets Manager
    @patch('book_charging_point.app.get_ssm_parameter')  # Mock SSM parameter call
    @patch('book_charging_point.app.get_secret_value')  # Mock Secrets Manager secret call
    def test_get_parameter_or_secret_no_env_var_param(self, mock_get_secret_value, mock_get_ssm_parameter, mock_get_parameter_or_secret):

        # Where environment variable is not set
        mock_get_ssm_parameter.return_value = 'some-param'
        mock_get_secret_value.return_value = 'some-secret' 

        # We should return the value from SSM
        value = get_parameter_or_secret('NON_EXISTING_VARIABLE')
        self.assertEqual(value, 'some-param')
        mock_get_ssm_parameter.assert_called_once()
        mock_get_secret_value.assert_not_called()

if __name__ == '__main__':
    unittest.main()
