"""Ensure the volume audit distinguishes scenarios from committed records."""

import unittest

from scripts.audit_data import audit_data


class DataAuditTests(unittest.TestCase):
    def test_current_inventory_and_schema_gaps_are_reported(self):
        result = audit_data()
        self.assertEqual(result["infrastructure_inventory"]["records"], 0)
        self.assertEqual(result["infrastructure_inventory"][
            "distinct_server_ids_embedded_in_scenarios"], 20)
        self.assertEqual(result["infrastructure_metrics"]["records"], 76)
        self.assertFalse(result["infrastructure_metrics"]["absolute_timestamp_present"])
        self.assertEqual(result["application_logs"]["records"], 78)
        self.assertFalse(result["application_logs"]["absolute_timestamp_present"])
        self.assertEqual(result["incident_records"]["simulated_alerts"], 20)
        self.assertFalse(result["incident_records"]["severity_present"])
        self.assertEqual(result["knowledge_base_documents"]["records"], 5)
        self.assertTrue(all(not category["volume_target_met"]
                            for category in result.values()))
