# Bun.lock Analyzer

A Python script to analyze `bun.lock` files and find packages released after a specific date.

## Features

- Extracts all packages and their versions from `bun.lock` file
- Queries the npm registry API to get release dates for each package version
- Filters packages released after a specified cutoff date
- Outputs results in JSON format

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Analyze a bun.lock file and find packages released after January 1, 2024:

```bash
python3 analyze_bun_lock.py bun.lock
```

### Specify a Custom Date

Find packages released after a specific date:

```bash
python3 analyze_bun_lock.py bun.lock --date 2024-06-01
```

### Save Results to a File

Save the results to a JSON file:

```bash
python3 analyze_bun_lock.py bun.lock --date 2024-01-01 --output results.json
```

### Verbose Mode

Show progress messages while processing:

```bash
python3 analyze_bun_lock.py bun.lock --verbose
```

### Combined Options

```bash
python3 analyze_bun_lock.py bun.lock --date 2024-06-01 --output results.json --verbose
```

## Command Line Arguments

- `lock_file` (required): Path to the bun.lock file
- `--date`: Cutoff date in ISO 8601 format (default: 2024-01-01)
- `--output`: Optional output file path for JSON results
- `--verbose`: Show progress messages during execution

## Output Format

The script outputs JSON with the following structure:

```json
{
  "cutoff_date": "2024-01-01",
  "total_packages": 150,
  "packages_after_date": 25,
  "packages": [
    {
      "package": "@babel/core",
      "version": "7.27.4",
      "release_date": "2024-06-15T10:30:45.123Z"
    },
    ...
  ]
}
```

## Example

```bash
# Find all packages released after July 1, 2024
python3 analyze_bun_lock.py bun.lock --date 2024-07-01 --verbose

# Output:
# Parsing bun.lock...
# Found 150 packages
# Fetching release date for @babel/core@7.27.4 (1/150)...
# ...
# 
# Summary:
# Total packages: 150
# Packages released after 2024-07-01: 8
```

## API Rate Limits

This script queries the npm registry API. Be aware of potential rate limits if analyzing large lock files. The script makes one API request per package, so processing may take some time for files with many packages.

## Error Handling

- If a package cannot be found in the npm registry, its release_date will be marked as "Unknown"
- If there's an error fetching data, the release_date will be marked as "Error"
- Packages with "Unknown" or "Error" dates are excluded from the filtered results

