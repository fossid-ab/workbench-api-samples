#!/usr/bin/env python3
"""
Simple tests for archive_stale_scans.py

This file contains essential tests for the utility script using the
Python standard library.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import tempfile
import json
import os
import sys

# Import the module under test
from archive_stale_scans import (
    SmartSampler, find_old_scans, process_scans, 
    create_scan_plan, save_plan_to_file, load_plan_from_file,
    make_api_call, list_scans, get_scan_info_batch
)


class TestSmartSampler(unittest.TestCase):
    """Test the core sampling logic."""
    
    def test_small_dataset_no_sampling(self):
        """Small datasets should return all indices."""
        sampler = SmartSampler()
        for size in [0, 50, 99]:
            indices = sampler.calculate_indices(size)
            self.assertEqual(indices, list(range(size)))
    
    def test_large_dataset_sampling(self):
        """Large datasets should use appropriate sampling."""
        sampler = SmartSampler()
        test_cases = [(100, 10), (1000, 100), (10000, 1000)]
        
        for total_scans, expected_samples in test_cases:
            indices = sampler.calculate_indices(total_scans)
            self.assertEqual(len(indices), expected_samples)
            self.assertTrue(all(0 <= idx < total_scans for idx in indices))


class TestArchitectureFunctions(unittest.TestCase):
    """Test the find_old_scans/process_scans architecture."""
    
    def create_scan_dataset(self, size: int):
        """Helper to create mock scan data."""
        return {f"scan_{i:03d}": {"code": f"scan_{i:03d}", "name": f"Scan {i}"} 
                for i in range(size)}
    
    def test_small_dataset_passthrough(self):
        """Small datasets should pass through find_old_scans unchanged."""
        scans = self.create_scan_dataset(50)
        result = find_old_scans(scans, "url", "user", "token", 365)
        self.assertEqual(result, scans)
    
    @patch('archive_stale_scans.get_scan_info_batch')
    def test_process_scans_age_filtering(self, mock_batch):
        """process_scans should correctly filter by age."""
        scans = self.create_scan_dataset(4)
        
        # Mock 2 old scans, 2 new scans
        def mock_response(url, username, token, scan_codes):
            results = {}
            for i, code in enumerate(scan_codes):
                is_old = i < 2
                date = "2022-01-01 10:00:00" if is_old else "2024-12-01 10:00:00"
                results[code] = {
                    "name": f"Test {code}",
                    "created": date,
                    "updated": date,
                    "is_archived": None,
                    "project_code": "TEST"
                }
            return results
        
        mock_batch.side_effect = mock_response
        
        result = process_scans(scans, "url", "user", "token", 365)
        self.assertEqual(len(result), 2)  # Only the old scans


class TestPlanManagement(unittest.TestCase):
    """Test plan creation and file operations."""
    
    def test_create_scan_plan(self):
        """Test plan creation from scan data."""
        old_scans = [
            ("PROJECT1", "Test Scan", "scan_001", 
             datetime(2022, 1, 1), datetime(2022, 6, 1))
        ]
        
        with patch('archive_stale_scans.get_project_info') as mock_proj:
            mock_proj.return_value = {"project_name": "Test Project"}
            
            plan = create_scan_plan(old_scans, "url", "user", "token")
            
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]["scan_name"], "Test Scan")
            self.assertEqual(plan[0]["project_name"], "Test Project")
    
    def test_plan_file_operations(self):
        """Test saving and loading plan files."""
        test_plan = [
            {
                "project_name": "Test Project",
                "scan_name": "Test Scan",
                "scan_code": "scan_001",
                "age_days": 500,
                "last_modified": "2022-06-01"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Test save
            save_plan_to_file(test_plan, temp_file)
            self.assertTrue(os.path.exists(temp_file))
            
            # Test load
            loaded_plan = load_plan_from_file(temp_file)
            self.assertEqual(loaded_plan, test_plan)
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestAPIFunctions(unittest.TestCase):
    """Test core API functions."""
    
    @patch('archive_stale_scans.session')
    def test_make_api_call_success(self, mock_session):
        """Test successful API call."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"test": "success"}}
        mock_session.post.return_value = mock_response
        
        result = make_api_call("http://test.com", {"test": "payload"})
        self.assertEqual(result, {"test": "success"})
    
    @patch('archive_stale_scans.make_api_call')
    def test_list_scans(self, mock_api):
        """Test scan listing with pagination."""
        # Mock paginated response - simulate a small page that triggers pagination end
        # First page: 2 scans (less than RECORDS_PER_PAGE=100, so pagination stops)
        mock_api.side_effect = [
            {"scan1": {"code": "scan1", "name": "Scan 1"}, "scan2": {"code": "scan2", "name": "Scan 2"}}
        ]
        
        result = list_scans("url", "user", "token")
        self.assertEqual(len(result), 2)  # Only 2 scans because pagination stops
        self.assertIn("scan1", result)
        self.assertIn("scan2", result)
        self.assertEqual(result["scan1"]["name"], "Scan 1")
    
    @patch('archive_stale_scans.make_api_call')
    def test_get_scan_info_batch(self, mock_api):
        """Test batch scan info retrieval."""
        mock_api.return_value = {
            "name": "Test Scan",
            "created": "2022-01-01 10:00:00",
            "updated": "2022-06-01 10:00:00"
        }
        
        result = get_scan_info_batch("url", "user", "token", ["scan1", "scan2"])
        self.assertEqual(len(result), 2)
        self.assertIn("scan1", result)
        self.assertEqual(result["scan1"]["name"], "Test Scan")


def run_tests():
    """Simple test runner that works without pytest."""
    print("🧪 Running Archive Stale Scans Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestSmartSampler,
        TestArchitectureFunctions, 
        TestPlanManagement,
        TestAPIFunctions
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed! The utility is ready to use.")
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False
    
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)