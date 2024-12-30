import json
import unittest
from unittest.mock import patch, MagicMock
from ingest_charging_point_availability_iot.app import lambda_handler, handle_connect, handle_disconnect, handle_message, append_event_to_dynamodb

class TestLambdaFunction(unittest.TestCase):

    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    def test_handle_connect(self, mock_table):

        mock_table.update_item.return_value = 'Updated'
        
        connection_id = 'test-connection-id'
        oocp_charge_point_id = 'CP123'
        timestamp = '2024-12-29T12:00:00Z'
        
        response = handle_connect(connection_id, oocp_charge_point_id, timestamp)
        
        # Check if update_item was called correctly
        mock_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression='SET  isConnected = :connected, statusUpdatedAt = :timestamp',
            ExpressionAttributeValues={
                ':connected': True,
                ':timestamp': timestamp
            }
        )
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Connected', response['body'])

    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    def test_handle_disconnect(self, mock_table):
        mock_table.update_item.return_value = 'Updated'
        
        connection_id = 'test-connection-id'
        oocp_charge_point_id = 'CP123'
        timestamp = '2024-12-29T12:00:00Z'
        
        response = handle_disconnect(connection_id, oocp_charge_point_id, timestamp)
        
        mock_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression='SET  isDisconnected = :disconnected, statusUpdatedAt = :timestamp',
            ExpressionAttributeValues={
                ':disconnected': True,
                ':timestamp': timestamp
            }
        )
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Disconnected', response['body'])

    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    def test_handle_message_status_notification(self, mock_table):

        mock_table.update_item.return_value = 'Updated'
        
        connection_id = 'test-connection-id'
        oocp_charge_point_id = 'CP123'
        timestamp = '2024-12-29T12:00:00Z'
        
        message_body = {
            'action': 'StatusNotification',
            'payload': {
                'status': 'Available'
            }
        }
        
        response = handle_message(connection_id, oocp_charge_point_id, timestamp, message_body)
        
        mock_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression=(
                'SET isAvailable = :available, '
                'statusUpdatedAt = :timestamp'
            ),
            ExpressionAttributeValues={
                ':available': True,
                ':timestamp': timestamp
            }
        )
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Message processed', response['body'])

    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    def test_handle_message_start_transaction_notification(self, mock_table):
        # Test for handling error notifications
        connection_id = 'test-connection-id'
        oocp_charge_point_id = 'CP123'
        timestamp = '2024-12-29T12:00:00Z'
        
        message_body = {
            'action': 'StartTransaction',
            'payload': {
                'some_content'
            }
        }
        
        response = handle_message(connection_id, oocp_charge_point_id, timestamp, message_body)
        
        # Assuming you have a way to log or handle errors in your implementation
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Message processed', response['body'])
    
    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    def test_handle_message_irrelevant_notification(self, mock_table):
        # Test for handling error notifications
        connection_id = 'test-connection-id'
        oocp_charge_point_id = 'CP123'
        timestamp = '2024-12-29T12:00:00Z'
        
        message_body = {
            'action': 'irrelevantAction',
            'payload': {
                'some_content'
            }
        }
        
        response = handle_message(connection_id, oocp_charge_point_id, timestamp, message_body)
        
        # Assuming you have a way to log or handle errors in your implementation
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('No action', response['body'])
    
    @patch('ingest_charging_point_availability_iot.app.charging_points_table')
    @patch('ingest_charging_point_availability_iot.app.charging_point_events_table')
    def test_lambda_handler_success(self, mock_charging_points_table, mock_charging_point_events_table):
        event = {
            'httpMethod': 'POST',
            'path': '/connect',
            'requestContext': {
                'routeKey': '$connect', 
                'connectionId': 'test-connection-id'
            }, 
            'body': json.dumps({
                'connectionId': 'test-connection-id',
                'oocpChargePointId': 'CP123',
                'timestamp': '2024-12-29T12:00:00Z'
            })
        }
        
        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('message', response['body'])
    
if __name__ == '__main__':
    unittest.main()
