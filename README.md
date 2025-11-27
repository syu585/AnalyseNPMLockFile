# Lock File Analyzer

A Python script to analyze lock files from various package managers and find packages released after a specific date.

## Supported Lock File Formats

- **Bun** (`bun.lock`)
- **npm** (`package-lock.json`)
- **Yarn** (`yarn.lock`)
- **pnpm** (`pnpm-lock.yaml`)
- **Deno** (`deno.lock`)

## Features

- Extracts all packages and their versions from various lock file formats
- **Auto-detection** of lock file format (or manual specification)
- **Concurrent querying** of npm registry API for fast performance (10x faster)
- Queries the npm registry API to get release dates for each package version
- Filters packages released after a specified cutoff date
- Outputs results in JSON format
- Configurable concurrency level for optimal performance

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Analyze any supported lock file (auto-detects format):

```bash
# Bun
python3 analyze_bun_lock.py bun.lock

# npm
python3 analyze_bun_lock.py package-lock.json

# Yarn
python3 analyze_bun_lock.py yarn.lock

# pnpm
python3 analyze_bun_lock.py pnpm-lock.yaml

# Deno
python3 analyze_bun_lock.py deno.lock
```

### Specify Format Explicitly

If auto-detection fails, or you want to force a specific format:

```bash
python3 analyze_bun_lock.py my-lock-file --format npm
python3 analyze_bun_lock.py my-lock-file --format yarn
python3 analyze_bun_lock.py my-lock-file --format pnpm
python3 analyze_bun_lock.py my-lock-file --format bun
python3 analyze_bun_lock.py my-lock-file --format deno
```

### Specify a Custom Date

Find packages released after a specific date:

```bash
python3 analyze_bun_lock.py package-lock.json --date 2024-06-01
```

### Save Results to a File

Save the results to a JSON file:

```bash
python3 analyze_bun_lock.py yarn.lock --date 2024-01-01 --output results.json
```

### Verbose Mode

Show progress messages while processing:

```bash
python3 analyze_bun_lock.py package-lock.json --verbose
```

### Control Concurrency

Adjust the number of concurrent workers (default: 10) for faster or more conservative querying:

```bash
# Faster processing with 20 concurrent workers
python3 analyze_bun_lock.py yarn.lock --workers 20 --verbose

# More conservative with 5 concurrent workers
python3 analyze_bun_lock.py pnpm-lock.yaml --workers 5
```

### Combined Options

```bash
python3 analyze_bun_lock.py package-lock.json --date 2024-06-01 --output results.json --verbose --workers 15 --format npm
```

## Command Line Arguments

- `lock_file` (required): Path to lock file (supports: bun.lock, package-lock.json, yarn.lock, pnpm-lock.yaml, deno.lock)
- `--format`: Lock file format - `bun`, `npm`, `yarn`, `pnpm`, `deno`, or `auto` (default: auto-detect)
- `--date` (required): Cutoff date in ISO 8601 format (e.g., 2024-01-01)
- `--output`: Optional output file path for JSON results
- `--verbose`: Show progress messages during execution
- `--workers`: Number of concurrent workers for fetching package data (default: 10)

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
# Find all packages released after July 1, 2024 in an npm lock file
python3 analyze_bun_lock.py package-lock.json --date 2024-07-01 --verbose

# Output:
# Parsing package-lock.json (auto-detecting format)...
# Format: npm
# Found 150 packages
# Fetching release dates for 150 packages using 10 concurrent workers...
# ✓ @babel/core@7.27.4
# ✓ react@18.2.0
# ...
# Progress: 10/150 packages fetched
# ...
# Completed fetching all 150 packages
# 
# Summary:
# Total packages: 150
# Packages released after 2024-07-01: 8
```

## Format Auto-Detection

The script automatically detects the lock file format based on:
1. **Filename** (e.g., `package-lock.json` → npm, `yarn.lock` → yarn)
2. **Content structure** (fallback if filename is ambiguous)

Supported formats and their typical filenames:
- **Bun**: `bun.lock`, `bun.lockb`
- **npm**: `package-lock.json`
- **Yarn**: `yarn.lock`
- **pnpm**: `pnpm-lock.yaml`
- **Deno**: `deno.lock`

If auto-detection fails or you want to override it, use the `--format` flag.

## Performance

The script uses concurrent HTTP requests (via `ThreadPoolExecutor`) to query the npm registry API in parallel, resulting in significant performance improvements:

- **Default**: 10 concurrent workers
- **Speed**: ~10x faster than sequential querying
- **Example**: 100 packages in ~10-20 seconds (vs. ~100-200 seconds sequentially)

You can adjust the concurrency level using the `--workers` flag:
- Higher values (e.g., `--workers 20`): Faster execution, more network load
- Lower values (e.g., `--workers 5`): More conservative, gentler on npm registry

## API Rate Limits

This script queries the npm registry API using concurrent requests for faster performance. The default of 10 concurrent workers is generally safe, but you may want to reduce this (using `--workers`) if you encounter rate limiting issues with very large lock files.

## Error Handling

- If a package cannot be found in the npm registry, its release_date will be marked as "Unknown"
- If there's an error fetching data, the release_date will be marked as "Error"
- Packages with "Unknown" or "Error" dates are excluded from the filtered results

