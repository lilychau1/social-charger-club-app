import json
import os
import boto3
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError
from book_charging_point.app import lambda_handler, update_dynamodb_status, send_oocp_reservation_request

dynamodb = boto3.resource('dynamodb')
charging_points_table = dynamodb.Table(os.environ.get('CHARGING_POINTS_TABLE_NAME', 'default-charging-points-table'))

def clean_up_dynamodb_charge_point(oocp_charge_point_id):
    """Clean up the test charge point data in DynamoDB"""
    try:
        charging_points_table.delete_item(
            Key={'oocpChargePointId': oocp_charge_point_id}
        )
    except ClientError as e:
        print(f"Error cleaning up DynamoDB charge point: {str(e)}")

@patch('book_charging_point.app.api_gateway_client')
def test_lambda_handler_success(self, mock_api_gateway_client):
    mock_api_response = MagicMock()
    mock_api_response['status'] = 200
    mock_api_response['body'] = json.dumps({'result': 'success'})
    mock_api_gateway_client.test_invoke_method.return_value = mock_api_response

    # Insert initial data into DynamoDB for testing
    charging_points_table.put_item(
        Item={
            'oocpChargePointId': 'test-point-id',
            'isAvailable': True,
            'statusUpdatedAt': '2024-12-30T00:00:00'
        }
    )

    # Define event to send to Lambda handler
    event = {
        'oocpChargePointId': 'test-point-id',
        'system': 'Virta',
        'connectorId': '1',
        'startTime': '2024-12-30T12:00:00',
        'endTime': '2024-12-30T13:00:00'
    }

    # Run the lambda handler with the event
    response = lambda_handler(event, None)

    # Assertions
    self.assertEqual(response['statusCode'], 200)
    self.assertIn('Slot booked successfully', response['body'])

    # Verify that the API call was made (mocked)
    mock_api_gateway_client.test_invoke_method.assert_called_once()

    # Verify DynamoDB was updated
    response = charging_points_table.get_item(Key={'oocpChargePointId': 'test-point-id'})
    item = response.get('Item')
    self.assertIsNotNone(item)
    self.assertEqual(item['isAvailable'], False)

    clean_up_dynamodb_charge_point('test-point-id')

@patch('book_charging_point.app.api_gateway_client')
def test_send_oocp_reservation_request_virta(self, mock_api_gateway_client):
    mock_api_response = MagicMock()
    mock_api_response['status'] = 200
    mock_api_response['body'] = json.dumps({'result': 'success'})
    mock_api_gateway_client.test_invoke_method.return_value = mock_api_response

    event = {
        'oocpChargePointId': 'test-point-id',
        'system': 'Virta', 
        'connectorId': '1',
        'startTime': '2024-12-30T12:00:00',
        'endTime': '2024-12-30T13:00:00'
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
def test_send_oocp_reservation_request_unsupported_system(self, mock_api_gateway_client):
    # Create event data with an unsupported system
    event = {
        'oocpChargePointId': 'test-point-id',
        'system': 'UnknownSystem',
        'connectorId': '1',
        'startTime': '2024-12-30T12:00:00',
        'endTime': '2024-12-30T13:00:00'
    }

    # Call the function to test
    with self.assertRaises(ValueError):
        send_oocp_reservation_request(
            event['system'],
            event['oocpChargePointId'],
            event['connectorId'],
            event['startTime'],
            event['endTime']
        )

if __name__ == '__main__':
    unittest.main()
