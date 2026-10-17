"""Offline compatibility checks; no personal data or provider credentials."""
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CollectorCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The upstream module initializes InfluxDB at import time.
        cls.db_patch = patch('influxdb.InfluxDBClient')
        cls.db = cls.db_patch.start()
        cls.collector = importlib.import_module('garmin_grafana.garmin_fetch')

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()

    def test_influx_v1_initialization(self):
        self.db.return_value.switch_database.assert_called_once()
        self.db.return_value.write_points.assert_called_once()

    def test_native_saved_token_login(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(self.collector, 'TOKEN_DIR', directory), patch.object(self.collector, 'Garmin') as client:
                result = self.collector.garmin_login()
                client.return_value.login.assert_called_once_with(directory)
                self.assertIs(result, client.return_value)

    def test_legacy_token_file_uses_separate_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / 'legacy-tokens'
            token.write_text('offline fixture')
            with patch.object(self.collector, 'TOKEN_DIR', str(token)), patch.object(self.collector, 'Garmin') as client:
                self.collector.garmin_login()
                client.return_value.login.assert_called_once_with(str(token) + '_tokens')
                self.assertEqual(token.read_text(), 'offline fixture')

    def test_failed_login_does_not_report_success(self):
        c = self.collector
        with patch.object(c, 'Garmin') as client, patch.object(c, 'GARMINCONNECT_EMAIL', 'offline@example.invalid'), patch.object(c, 'GARMINCONNECT_PASSWORD', 'offline-fixture'):
            client.return_value.login.side_effect = c.GarminConnectAuthenticationError('offline rejected')
            with self.assertRaisesRegex(Exception, 'Garmin login failed'):
                c.garmin_login()

    def test_date_iteration(self):
        self.assertEqual(list(self.collector.iter_days('2024-02-28', '2024-03-01')), ['2024-03-01', '2024-02-29', '2024-02-28'])

    def test_upstream_bulk_activity_unit_conversion(self):
        import json
        with patch.dict("sys.modules", {"garmin_fetch": self.collector}):
            from garmin_grafana.garmin_bulk_importer import GarminBulkExport
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'DI-Connect-Fitness-summarizedActivities.json'
            source.write_text(json.dumps([{'summarizedActivitiesExport': [{
                'startTimeGmt': 1704067200000, 'activityType': 'running',
                'distance': 100000, 'duration': 600000, 'elapsedDuration': 660000,
                'avgSpeed': 0.15, 'calories': 419, 'hrTimeInZone_1': 30000,
            }]}]))
            importer = GarminBulkExport.__new__(GarminBulkExport)
            importer.all_files = [source]
            activity = importer.load_activities()[0]
            self.assertEqual(activity['distance'], 1000)
            self.assertEqual(activity['duration'], 600)
            self.assertEqual(activity['elapsedDuration'], 660)
            self.assertEqual(activity['averageSpeed'], 1.5)
            self.assertAlmostEqual(activity['calories'], 100)
            self.assertEqual(activity['hrTimeInZone_1'], 30)

    def test_arrow_round_trip(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.table({'heart_rate': [60, 75], 'day': ['2026-01-01', '2026-01-02']})
        output = pa.BufferOutputStream()
        pq.write_table(table, output)
        self.assertEqual(pq.read_table(pa.BufferReader(output.getvalue())).to_pylist(), table.to_pylist())

    def test_msgpack_influx_payload_round_trip(self):
        import msgpack
        payload = {'measurement': 'HeartRate', 'fields': {'value': 60}, 'tags': {'Device': 'offline'}}
        self.assertEqual(msgpack.unpackb(msgpack.packb(payload, use_bin_type=True), raw=False), payload)

    def test_influx_v3_client_constructs_without_network(self):
        from influxdb_client_3 import InfluxDBClient3
        client = InfluxDBClient3(host='http://127.0.0.1:1', token='offline-fixture', database='offline')
        client.close()


if __name__ == '__main__':
    unittest.main()
