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


def get_package_release_date(package_name: str, version: str) -> str:
    """
    Query npm registry API to get the release date for a specific package version.
    
    Args:
        package_name: Name of the npm package
        version: Version of the package
        
    Returns:
        Release date as ISO 8601 string, or "Unknown" if not found
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
            return data['time'][version]
        else:
            return "Unknown"
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {package_name}@{version}: {e}", file=sys.stderr)
        return "Error"
    except Exception as e:
        print(f"Unexpected error for {package_name}@{version}: {e}", file=sys.stderr)
        return "Error"


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
    
    args = parser.parse_args()
    
    # Parse bun.lock file
    if args.verbose:
        print(f"Parsing {args.lock_file}...", file=sys.stderr)
    
    packages = parse_bun_lock(args.lock_file)
    
    if args.verbose:
        print(f"Found {len(packages)} packages", file=sys.stderr)
    
    # Get release dates for all packages
    packages_with_dates = []
    
    for i, (package_name, version) in enumerate(packages, 1):
        if args.verbose:
            print(f"Fetching release date for {package_name}@{version} ({i}/{len(packages)})...", file=sys.stderr)
        
        release_date = get_package_release_date(package_name, version)
        
        packages_with_dates.append({
            'package': package_name,
            'version': version,
            'release_date': release_date
        })
    
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

