#!/usr/bin/env python3
"""
Script to analyze bun.lock file:
- Extract all packages with their versions
- Query release time for each version using npm registry API
- Find packages released after a specific date
"""

import json
import re
import requests
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import quote


def parse_bun_lock(lock_file_path: str) -> List[Tuple[str, str]]:
    """
    Parse bun.lock file and extract package names with their versions.
    Handles JavaScript-like JSON with trailing commas.
    
    Args:
        lock_file_path: Path to the bun.lock file
        
    Returns:
        List of (package_name, version) tuples
    """
    with open(lock_file_path, 'r') as f:
        content = f.read()
        
    # Remove trailing commas before closing braces/brackets (JavaScript-style JSON)
    # This regex handles trailing commas in objects and arrays
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    try:
        lock_data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error parsing bun.lock file: {e}", file=sys.stderr)
        print("The file may have syntax that's not compatible with JSON.", file=sys.stderr)
        sys.exit(1)
    
    packages = []
    
    # Parse the packages section
    if 'packages' in lock_data:
        for package_key, package_info in lock_data['packages'].items():
            if isinstance(package_info, list) and len(package_info) > 0:
                # Format: ["package@version", ...]
                package_full_name = package_info[0]
                
                # Extract package name and version
                if '@' in package_full_name:
                    # Handle scoped packages (e.g., @babel/core@7.27.4)
                    if package_full_name.startswith('@'):
                        parts = package_full_name.rsplit('@', 1)
                        if len(parts) == 2:
                            package_name = parts[0]
                            version = parts[1]
                            packages.append((package_name, version))
                    else:
                        parts = package_full_name.split('@')
                        if len(parts) >= 2:
                            package_name = parts[0]
                            version = parts[1]
                            packages.append((package_name, version))
    
    return packages


def get_package_release_date(package_name: str, version: str, verbose: bool = False) -> Dict:
    """
    Query npm registry API to get the release date for a specific package version.
    
    Args:
        package_name: Name of the npm package
        version: Version of the package
        verbose: Whether to print progress messages
        
    Returns:
        Dictionary with package info including release date
    """
    try:
        # Encode package name for URL (important for scoped packages)
        encoded_name = quote(package_name, safe='@/')
        url = f"https://registry.npmjs.org/{encoded_name}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Get the time information for the specific version
        if 'time' in data and version in data['time']:
            release_date = data['time'][version]
        else:
            release_date = "Unknown"
        
        if verbose:
            print(f"✓ {package_name}@{version}", file=sys.stderr)
            
        return {
            'package': package_name,
            'version': version,
            'release_date': release_date
        }
            
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"✗ {package_name}@{version}: {e}", file=sys.stderr)
        return {
            'package': package_name,
            'version': version,
            'release_date': "Error"
        }
    except Exception as e:
        if verbose:
            print(f"✗ {package_name}@{version}: {e}", file=sys.stderr)
        return {
            'package': package_name,
            'version': version,
            'release_date': "Error"
        }


def fetch_release_dates_concurrent(packages: List[Tuple[str, str]], max_workers: int = 10, verbose: bool = False) -> List[Dict]:
    """
    Fetch release dates for multiple packages concurrently.
    
    Args:
        packages: List of (package_name, version) tuples
        max_workers: Maximum number of concurrent workers (default: 10)
        verbose: Whether to print progress messages
        
    Returns:
        List of package dictionaries with release dates
    """
    packages_with_dates = []
    
    if verbose:
        print(f"Fetching release dates for {len(packages)} packages using {max_workers} concurrent workers...", file=sys.stderr)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_package = {
            executor.submit(get_package_release_date, pkg_name, version, verbose): (pkg_name, version)
            for pkg_name, version in packages
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_package):
            completed += 1
            try:
                result = future.result()
                packages_with_dates.append(result)
                
                if verbose and completed % 10 == 0:
                    print(f"Progress: {completed}/{len(packages)} packages fetched", file=sys.stderr)
            except Exception as e:
                pkg_name, version = future_to_package[future]
                print(f"Error processing {pkg_name}@{version}: {e}", file=sys.stderr)
                packages_with_dates.append({
                    'package': pkg_name,
                    'version': version,
                    'release_date': "Error"
                })
    
    if verbose:
        print(f"Completed fetching all {len(packages)} packages", file=sys.stderr)
    
    return packages_with_dates


def filter_packages_after_date(packages_with_dates: List[Dict], cutoff_date: str) -> List[Dict]:
    """
    Filter packages released after a specific date.
    
    Args:
        packages_with_dates: List of package dictionaries with release dates
        cutoff_date: ISO 8601 date string (e.g., "2024-01-01")
        
    Returns:
        List of packages released after the cutoff date
    """
    from datetime import timezone
    
    try:
        # Parse cutoff date and make it timezone-aware (UTC)
        cutoff = datetime.fromisoformat(cutoff_date.replace('Z', '+00:00'))
        # If the parsed datetime is naive (no timezone), make it UTC
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"Invalid date format: {cutoff_date}. Use ISO 8601 format (e.g., '2024-01-01')", file=sys.stderr)
        return []
    
    filtered = []
    for pkg in packages_with_dates:
        if pkg['release_date'] not in ['Unknown', 'Error']:
            try:
                release = datetime.fromisoformat(pkg['release_date'].replace('Z', '+00:00'))
                # Ensure release date is timezone-aware
                if release.tzinfo is None:
                    release = release.replace(tzinfo=timezone.utc)
                    
                if release > cutoff:
                    filtered.append(pkg)
            except ValueError:
                continue
    
    return filtered


def main():
    """Main function to run the analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze bun.lock file and find packages released after a specific date'
    )
    parser.add_argument(
        'lock_file',
        help='Path to bun.lock file'
    )
    parser.add_argument(
        '--date',
        default='2024-01-01',
        help='Cutoff date in ISO 8601 format (e.g., 2024-01-01). Packages released after this date will be listed.'
    )
    parser.add_argument(
        '--output',
        help='Optional output file path (JSON format). If not specified, prints to stdout.'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show progress messages'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of concurrent workers for fetching package data (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Parse bun.lock file
    if args.verbose:
        print(f"Parsing {args.lock_file}...", file=sys.stderr)
    
    packages = parse_bun_lock(args.lock_file)
    
    if args.verbose:
        print(f"Found {len(packages)} packages", file=sys.stderr)
    
    # Get release dates for all packages concurrently
    packages_with_dates = fetch_release_dates_concurrent(
        packages, 
        max_workers=args.workers, 
        verbose=args.verbose
    )
    
    # Filter packages by date
    if args.verbose:
        print(f"\nFiltering packages released after {args.date}...", file=sys.stderr)
    
    filtered_packages = filter_packages_after_date(packages_with_dates, args.date)
    
    # Sort by release date (newest first)
    filtered_packages.sort(key=lambda x: x['release_date'], reverse=True)
    
    # Prepare output
    output_data = {
        'cutoff_date': args.date,
        'total_packages': len(packages),
        'packages_after_date': len(filtered_packages),
        'packages': filtered_packages
    }
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        if args.verbose:
            print(f"\nResults written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output_data, indent=2))
    
    # Print summary
    if args.verbose:
        print(f"\nSummary:", file=sys.stderr)
        print(f"Total packages: {len(packages)}", file=sys.stderr)
        print(f"Packages released after {args.date}: {len(filtered_packages)}", file=sys.stderr)


if __name__ == '__main__':
    main()

