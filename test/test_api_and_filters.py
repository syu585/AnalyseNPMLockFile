#!/usr/bin/env python3
"""
Unit tests for package release date fetching and filtering functions.
"""

import unittest
import sys
import os
from unittest.mock import patch, Mock
from datetime import datetime, timezone

# Add parent directory to path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyze_lock import (
    get_package_release_date,
    fetch_release_dates_concurrent,
    filter_packages_after_date
)


class TestGetPackageReleaseDate(unittest.TestCase):
    """Test package release date fetching from npm registry."""
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_success(self, mock_get):
        """Test successful package release date fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'time': {
                '18.2.0': '2022-06-14T15:30:00.000Z'
            }
        }
        mock_get.return_value = mock_response
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['package'], 'react')
        self.assertEqual(result['version'], '18.2.0')
        self.assertEqual(result['release_date'], '2022-06-14T15:30:00.000Z')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_scoped_package(self, mock_get):
        """Test fetching release date for scoped package."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'time': {
                '7.27.4': '2024-01-15T10:20:30.000Z'
            }
        }
        mock_get.return_value = mock_response
        
        result = get_package_release_date('@babel/core', '7.27.4')
        
        self.assertEqual(result['package'], '@babel/core')
        self.assertEqual(result['version'], '7.27.4')
        self.assertEqual(result['release_date'], '2024-01-15T10:20:30.000Z')
        
        # Verify URL encoding was used
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        self.assertIn('@babel/core', call_args)
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_not_found(self, mock_get):
        """Test handling when version is not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'time': {
                '1.0.0': '2020-01-01T00:00:00.000Z'
            }
        }
        mock_get.return_value = mock_response
        
        result = get_package_release_date('some-package', '2.0.0')
        
        self.assertEqual(result['release_date'], 'Unknown')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_network_error(self, mock_get):
        """Test handling network errors."""
        mock_get.side_effect = Exception('Network error')
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_timeout(self, mock_get):
        """Test handling timeout errors."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_verbose(self, mock_get):
        """Test verbose output."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'time': {
                '18.2.0': '2022-06-14T15:30:00.000Z'
            }
        }
        mock_get.return_value = mock_response
        
        with patch('sys.stderr'):
            result = get_package_release_date('react', '18.2.0', verbose=True)
        
        self.assertEqual(result['release_date'], '2022-06-14T15:30:00.000Z')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_http_404(self, mock_get):
        """Test handling 404 errors for non-existent packages."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response
        
        result = get_package_release_date('nonexistent-package', '1.0.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_http_500(self, mock_get):
        """Test handling server errors."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_connection_error(self, mock_get):
        """Test handling connection errors."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_json_decode_error(self, mock_get):
        """Test handling invalid JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_get.return_value = mock_response
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Error')
    
    @patch('analyze_lock.requests.get')
    def test_get_package_release_date_missing_time_field(self, mock_get):
        """Test handling responses without time field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'react',
            'versions': {'18.2.0': {}}
            # Missing 'time' field
        }
        mock_get.return_value = mock_response
        
        result = get_package_release_date('react', '18.2.0')
        
        self.assertEqual(result['release_date'], 'Unknown')


class TestFetchReleaseDatesConcurrent(unittest.TestCase):
    """Test concurrent package release date fetching."""
    
    @patch('analyze_lock.get_package_release_date')
    def test_fetch_release_dates_concurrent_basic(self, mock_get_date):
        """Test basic concurrent fetching."""
        mock_get_date.return_value = {
            'package': 'test-pkg',
            'version': '1.0.0',
            'release_date': '2024-01-01T00:00:00.000Z'
        }
        
        packages = [
            ('react', '18.2.0'),
            ('lodash', '4.17.21')
        ]
        
        results = fetch_release_dates_concurrent(packages, max_workers=2, verbose=False)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(mock_get_date.call_count, 2)
    
    @patch('analyze_lock.get_package_release_date')
    def test_fetch_release_dates_concurrent_empty(self, mock_get_date):
        """Test with empty package list."""
        packages = []
        
        results = fetch_release_dates_concurrent(packages, max_workers=2, verbose=False)
        
        self.assertEqual(len(results), 0)
        mock_get_date.assert_not_called()
    
    @patch('analyze_lock.get_package_release_date')
    def test_fetch_release_dates_concurrent_error_handling(self, mock_get_date):
        """Test error handling in concurrent fetching."""
        def side_effect(*args, **kwargs):
            if args[0] == 'failing-package':
                raise Exception('Test error')
            return {
                'package': args[0],
                'version': args[1],
                'release_date': '2024-01-01T00:00:00.000Z'
            }
        
        mock_get_date.side_effect = side_effect
        
        packages = [
            ('react', '18.2.0'),
            ('failing-package', '1.0.0'),
            ('lodash', '4.17.21')
        ]
        
        # Should handle the error and continue with other packages
        results = fetch_release_dates_concurrent(packages, max_workers=2, verbose=False)
        
        # All 3 packages should be in results (including the failing one)
        self.assertEqual(len(results), 3)
        
        # Verify the failing package has Error status
        error_pkg = next((p for p in results if p['package'] == 'failing-package'), None)
        self.assertIsNotNone(error_pkg)
        self.assertEqual(error_pkg['release_date'], 'Error')
        
        # Verify successful packages
        successful_pkgs = [p for p in results if p['release_date'] != 'Error']
        self.assertEqual(len(successful_pkgs), 2)


class TestFilterPackagesAfterDate(unittest.TestCase):
    """Test package filtering by release date."""
    
    def test_filter_packages_after_date_basic(self):
        """Test basic filtering of packages."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'lodash',
                'version': '4.17.21',
                'release_date': '2023-01-01T00:00:00.000Z'
            },
            {
                'package': 'axios',
                'version': '1.0.0',
                'release_date': '2024-08-01T12:00:00.000Z'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 2)
        
        package_names = [pkg['package'] for pkg in filtered]
        self.assertIn('react', package_names)
        self.assertIn('axios', package_names)
        self.assertNotIn('lodash', package_names)
    
    def test_filter_packages_after_date_exclude_unknown(self):
        """Test that packages with 'Unknown' dates are excluded."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'unknown-pkg',
                'version': '1.0.0',
                'release_date': 'Unknown'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['package'], 'react')
    
    def test_filter_packages_after_date_exclude_error(self):
        """Test that packages with 'Error' dates are excluded."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'error-pkg',
                'version': '1.0.0',
                'release_date': 'Error'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['package'], 'react')
    
    def test_filter_packages_after_date_excludes_exact_cutoff(self):
        """Test that packages released exactly at cutoff date are excluded (uses > not >=)."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-01-01T00:00:00.000Z'
            }
        ]
        
        cutoff_date = '2024-01-01T00:00:00.000Z'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        # Package released exactly at cutoff should not be included (> not >=)
        self.assertEqual(len(filtered), 0)
    
    def test_filter_packages_after_date_includes_one_second_after(self):
        """Test that packages released one second after cutoff are included."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-01-01T00:00:01.000Z'  # 1 second after cutoff
            }
        ]
        
        cutoff_date = '2024-01-01T00:00:00.000Z'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        # Package released 1 second after cutoff should be included
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['package'], 'react')
    
    def test_filter_packages_after_date_invalid_date(self):
        """Test handling of invalid cutoff date."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            }
        ]
        
        cutoff_date = 'invalid-date'
        
        with patch('sys.stderr'):
            filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 0)
    
    def test_filter_packages_after_date_timezone_aware(self):
        """Test that timezone handling works correctly."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'vue',
                'version': '3.0.0',
                'release_date': '2024-06-15T10:30:00+05:00'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        # Both should be included
        self.assertEqual(len(filtered), 2)
    
    def test_filter_packages_after_date_empty_list(self):
        """Test with empty package list."""
        packages = []
        cutoff_date = '2024-01-01'
        
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 0)
    
    def test_filter_packages_after_date_all_before(self):
        """Test when all packages are before cutoff date."""
        packages = [
            {
                'package': 'react',
                'version': '16.0.0',
                'release_date': '2020-01-01T00:00:00.000Z'
            },
            {
                'package': 'lodash',
                'version': '4.0.0',
                'release_date': '2019-01-01T00:00:00.000Z'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 0)
    
    def test_filter_packages_after_date_all_after(self):
        """Test when all packages are after cutoff date."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'lodash',
                'version': '4.17.21',
                'release_date': '2024-07-01T00:00:00.000Z'
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        self.assertEqual(len(filtered), 2)
    
    def test_filter_packages_after_date_malformed_package_dict(self):
        """Test handling of packages with missing fields.
        
        Note: The current implementation expects all packages to have 'release_date' field.
        This test verifies that behavior and documents that malformed packages will raise KeyError.
        """
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'broken-pkg',
                # Missing version field
                'release_date': '2024-07-01T00:00:00.000Z'
            },
            {
                'version': '1.0.0',
                # Missing package field
                'release_date': '2024-08-01T00:00:00.000Z'
            },
            {
                'package': 'no-date-pkg',
                'version': '2.0.0'
                # Missing release_date field - this will cause KeyError
            }
        ]
        
        cutoff_date = '2024-01-01'
        
        # The current implementation doesn't handle missing 'release_date' gracefully
        # It will raise KeyError when accessing pkg['release_date']
        with self.assertRaises(KeyError):
            filtered = filter_packages_after_date(packages, cutoff_date)
    
    def test_filter_packages_after_date_empty_string_values(self):
        """Test handling of packages with empty string values.
        
        Note: The implementation checks if release_date is 'Unknown' or 'Error',
        but empty string '' does not match either, so it tries to parse it as a date.
        Empty strings cause ValueError which is caught and the package is skipped.
        """
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'empty-package',
                'version': '1.0.0',
                'release_date': ''  # Empty string will cause ValueError, package skipped
            },
            {
                'package': 'empty-version',
                'version': '',
                'release_date': '2024-08-01T00:00:00.000Z'
            },
            {
                'package': 'empty-date',
                'version': '2.0.0',
                'release_date': ''  # Empty string will cause ValueError, package skipped
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        # Implementation silently skips packages with empty or invalid date strings (catches ValueError)
        # So we should get 2 packages: react and empty-version (which has valid date but empty version)
        self.assertEqual(len(filtered), 2)
        package_names = [pkg['package'] for pkg in filtered]
        self.assertIn('react', package_names)
        self.assertIn('empty-version', package_names)
    
    def test_filter_packages_after_date_invalid_release_date_format(self):
        """Test handling of packages with invalid date formats."""
        packages = [
            {
                'package': 'react',
                'version': '18.2.0',
                'release_date': '2024-06-15T10:30:00.000Z'
            },
            {
                'package': 'invalid-date',
                'version': '1.0.0',
                'release_date': 'not-a-date'
            },
            {
                'package': 'partial-date',
                'version': '2.0.0',
                'release_date': '2024-13-45'  # Invalid month/day
            }
        ]
        
        cutoff_date = '2024-01-01'
        filtered = filter_packages_after_date(packages, cutoff_date)
        
        # Only the valid package should be included
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['package'], 'react')


if __name__ == '__main__':
    unittest.main()

