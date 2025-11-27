# Test Suite

Comprehensive unit tests for the lock file analyzer.

## Test Coverage

### `test_parsers.py`
Tests for lock file parsing functions:
- `TestDetectLockFileFormat` - Auto-detection of lock file formats
- `TestParseBunLock` - Bun lock file parsing
- `TestParseNpmLock` - npm package-lock.json parsing (v6 and v7+)
- `TestParseYarnLock` - Yarn lock file parsing
- `TestParsePnpmLock` - pnpm lock file parsing
- `TestParsePnpmLock` - Deno lock file parsing
- `TestParseLockFile` - Unified parser with auto-detection

### `test_api_and_filters.py`
Tests for API interaction and filtering functions:
- `TestGetPackageReleaseDate` - npm registry API queries with mocking
- `TestFetchReleaseDatesConcurrent` - Concurrent package fetching
- `TestFilterPackagesAfterDate` - Date-based filtering logic

## Running Tests

### Run All Tests
```bash
# From project root
python test/run_tests.py

# Or using unittest directly
python -m unittest discover test

# Or using pytest (if installed)
pytest test/
```

### Run Specific Test File
```bash
python -m unittest test.test_parsers
python -m unittest test.test_api_and_filters
```

### Run Specific Test Class
```bash
python -m unittest test.test_parsers.TestParseBunLock
python -m unittest test.test_api_and_filters.TestFilterPackagesAfterDate
```

### Run Specific Test Method
```bash
python -m unittest test.test_parsers.TestParseBunLock.test_parse_bun_lock_basic
```

### Run with Verbose Output
```bash
python -m unittest discover test -v
```

## Test Fixtures

Sample lock files are stored in `test/fixtures/`:
- `sample_bun.lock` - Bun lock file
- `sample_package_lock.json` - npm package-lock.json
- `sample_yarn.lock` - Yarn lock file
- `sample_pnpm_lock.yaml` - pnpm lock file
- `sample_deno.lock` - Deno lock file

## Mocking

API calls to the npm registry are mocked using `unittest.mock` to:
- Avoid hitting real API endpoints during tests
- Test error handling without causing real errors
- Make tests fast and deterministic

## Coverage

To check test coverage (requires `coverage` package):

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run -m unittest discover test

# View coverage report
coverage report

# Generate HTML coverage report
coverage html
```

## Adding New Tests

When adding new functions to `analyze_bun_lock.py`:

1. Add corresponding test class to appropriate test file
2. Create test methods for:
   - Happy path (normal operation)
   - Edge cases (empty inputs, boundary conditions)
   - Error cases (invalid input, network errors)
   - Special cases (scoped packages, version formats, etc.)

Example test structure:
```python
class TestNewFunction(unittest.TestCase):
    """Test new_function."""
    
    def test_normal_case(self):
        """Test normal operation."""
        result = new_function('input')
        self.assertEqual(result, expected)
    
    def test_edge_case(self):
        """Test edge case."""
        result = new_function('')
        self.assertEqual(result, expected)
    
    def test_error_case(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            new_function(invalid_input)
```

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    python -m unittest discover test
```

