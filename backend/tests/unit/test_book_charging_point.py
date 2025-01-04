import unittest
from unittest.mock import patch, MagicMock, ANY
import os
import json
from lambda_functions.book_charging_point.app import (
    lambda_handler,
    update_dynamodb_charging_points_table_status,
    get_parameter_or_secret,
    book_charging_point,
)

class TestBookChargingPoint(unittest.TestCase):

    @patch('lambda_functions.book_charging_point.app.requests.post')
    @patch('lambda_functions.book_charging_point.app.log_booking_to_dynamodb')
    @patch('lambda_functions.book_charging_point.app.update_dynamodb_charging_points_table_status')
    def test_lambda_handler_success(self, mock_update_status, mock_log_booking, mock_requests_post):
        mock_requests_post.return_value = MagicMock(status_code=200, json=lambda: {"message": "Success"})
        mock_update_status.return_value = None
        mock_log_booking.return_value = None

        event = {
            'httpMethod': 'POST', 
            'body': json.dumps({
                'consumerId': 'test-consumer-id',
                'oocpChargePointId': 'test-point-id',
                'system': 'Virta',
                'connectorId': '1',
                'startTime': '2024-12-30T12:00:00',
                'endTime': '2024-12-30T13:00:00'  
            })
        }
        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Slot booked successfully', response['body'])
        mock_update_status.assert_called_once()
        mock_log_booking.assert_called_once()

    @patch('lambda_functions.book_charging_point.app.charging_points_table')
    def test_update_dynamodb_charging_points_table_status(self, mock_table):
        mock_table.update_item.return_value = None
        timestamp = '2024-01-01T00:00:00'
        consumer_id = 'consumer-123'

        update_dynamodb_charging_points_table_status('point-id', False, timestamp, consumer_id)

        mock_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': 'point-id'},
            UpdateExpression="SET isAvailable = :is_available, statusUpdatedAt = :timestamp, currentBookedConsumerId = :consumer_id",
            ExpressionAttributeValues={
                ':is_available': False,
                ':timestamp': timestamp,
                ':consumer_id': consumer_id
            },
            ConditionExpression="attribute_exists(oocpChargePointId)"
        )

    @patch('lambda_functions.book_charging_point.app.get_parameter_or_secret')
    @patch('lambda_functions.book_charging_point.app.requests.post')
    def test_book_charging_point_virta(self, mock_requests_post, mock_get_parameter_or_secret):
        mock_get_parameter_or_secret.return_value = 'mocked-secret'
        mock_requests_post.return_value = MagicMock(status_code=200, json=lambda: {"message": "Reserved"})

        response = book_charging_point('Virta', 'test-id', '1', '2024-12-30T12:00:00', '2024-12-30T13:00:00')

        self.assertEqual(response['status'], 'success')
        mock_requests_post.assert_called_once()

    @patch('lambda_functions.book_charging_point.app.get_parameter_or_secret')
    @patch('lambda_functions.book_charging_point.app.requests.post')
    def test_book_charging_point_invalid_system(self, mock_requests_post, mock_get_parameter_or_secret):
        with self.assertRaises(ValueError) as context:
            book_charging_point('InvalidSystem', 'test-id', '1', '2024-12-30T12:00:00', '2024-12-30T13:00:00')
        self.assertEqual(str(context.exception), 'Unsupported system: InvalidSystem')

    @patch('lambda_functions.book_charging_point.app.get_parameter_or_secret')
    def test_get_parameter_or_secret_env(self, mock_get_parameter_or_secret):
        os.environ['TEST_PARAM'] = 'env-value'
        result = get_parameter_or_secret('TEST_PARAM')
        self.assertEqual(result, 'env-value')

    @patch('lambda_functions.book_charging_point.app.ssm_client.get_parameter')
    @patch('lambda_functions.book_charging_point.app.secrets_client.get_secret_value')
    def test_get_parameter_or_secret_fallbacks(self, mock_get_secret_value, mock_get_ssm_parameter):
        os.environ.pop('TEST_PARAM', None)  # Ensure the env variable is not set
        mock_get_ssm_parameter.return_value = {'Parameter': {'Value': 'ssm-value'}}
        mock_get_secret_value.return_value = {'SecretString': json.dumps({'TEST_PARAM': 'secret-value'})}

        result = get_parameter_or_secret('TEST_PARAM')
        self.assertEqual(result, 'ssm-value')
        mock_get_ssm_parameter.assert_called_once()
        mock_get_secret_value.assert_not_called()

if __name__ == '__main__':
    unittest.main()
