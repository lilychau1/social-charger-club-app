import json
import unittest
from unittest.mock import patch, MagicMock, ANY
from lambda_functions.ingest_charging_point_availability_iot.app import lambda_handler, handle_device_status, handle_action, extract_oocp_charge_point_id_from_topic

class TestLambdaFunction(unittest.TestCase):

    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_points_table')
    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_point_events_table')
    def test_handle_device_status_online(self, mock_charging_point_events_table, mock_charging_points_table):

        mock_charging_points_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_charging_point_events_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        oocp_charge_point_id = 'CP123'
        status = 'online'

        response = handle_device_status(oocp_charge_point_id, status)

        mock_charging_points_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression='SET isConnected = :connected, statusUpdatedAt = :timestamp',
            ExpressionAttributeValues={
                ':connected': True,
                ':timestamp': ANY
            }
        )

        mock_charging_point_events_table.put_item.assert_called_once_with(
            Item={
                'eventId': ANY,  # We use ANY since UUID is generated dynamically
                'oocpChargePointId': oocp_charge_point_id,
                'timestamp': ANY,
                'eventType': 'connect',
                'message': {'status': status}
            }
        )

    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_points_table')
    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_point_events_table')
    def test_handle_device_status_offline(self, mock_charging_point_events_table, mock_charging_points_table):
        mock_charging_points_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_charging_point_events_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        oocp_charge_point_id = 'CP123'
        status = 'offline'
        
        response = handle_device_status(oocp_charge_point_id, status)

        mock_charging_points_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression='SET isConnected = :connected, statusUpdatedAt = :timestamp',
            ExpressionAttributeValues={
                ':connected': False,
                ':timestamp': ANY
            }
        )

        mock_charging_point_events_table.put_item.assert_called_once_with(
            Item={
                'eventId': ANY,  # UUID is dynamically generated
                'oocpChargePointId': oocp_charge_point_id,
                'timestamp': ANY,
                'eventType': 'disconnect',
                'message': {'status': status}
            }
        )

    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_points_table')
    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_point_events_table')
    def test_handle_action_start_transaction(self, mock_charging_point_events_table, mock_charging_points_table):

        mock_charging_points_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        mock_charging_point_events_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        oocp_charge_point_id = 'CP123'
        action = 'StartTransaction'
        
        message_body = {
            'action': action,
            'payload': {}
        }

        response = handle_action(action, oocp_charge_point_id, message_body)

        mock_charging_points_table.update_item.assert_called_once_with(
            Key={'oocpChargePointId': oocp_charge_point_id},
            UpdateExpression='SET isAvailable = :available, statusUpdatedAt = :timestamp',
            ExpressionAttributeValues={
                ':available': False,
                ':timestamp': ANY
            }
        )

        mock_charging_point_events_table.put_item.assert_called_once_with(
            Item={
                'eventId': ANY,
                'oocpChargePointId': oocp_charge_point_id,
                'timestamp': ANY,
                'eventType': action,
                'message': message_body
            }
        )

    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_points_table')
    @patch('lambda_functions.ingest_charging_point_availability_iot.app.charging_point_events_table')
    def test_lambda_handler_success(self, mock_charging_points_table, mock_charging_point_events_table):
        event = {
            'Records': [
                {
                    'topic': 'charging_points/CP123/status',
                    'message': json.dumps({'status': 'online'})
                },
                {
                    'topic': 'charging_points/CP123/action',
                    'message': json.dumps({'action': 'StartTransaction', 'payload': {}})
                }
            ]
        }

        # Simulate Lambda execution
        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Messages processed successfully', response['body'])

if __name__ == '__main__':
    unittest.main()
