#!/usr/bin/env python3
"""
Recursive HTTP/FTP Directory Downloader
Downloads entire directory structures from HTTP or FTP servers
"""

import os
import sys
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import argparse
from pathlib import Path
from typing import Set, Tuple
import hashlib

class RecursiveDownloader:
    def __init__(self, output_dir: str = "downloads", delay: float = 0.05,
                 max_retries: int = 3, skip_existing: bool = True):
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.max_retries = max_retries
        self.skip_existing = skip_existing
        self.base_url = None  # Store original base URL

        # Statistics
        self.total_files = 0
        self.files_downloaded = 0
        self.files_skipped = 0
        self.total_bytes = 0
        self.failed_downloads = []
        self.visited_urls: Set[str] = set()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_size(self, size_bytes: int) -> str:
        """Format size in human readable format"""
        if size_bytes == 0:
            return "0 B"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def get_local_path(self, url: str) -> Path:
        """Convert URL to local file path, preserving directory structure"""
        parsed_base = urlparse(self.base_url)
        parsed_url = urlparse(url)

        # Get the path relative to base URL
        base_path = parsed_base.path.rstrip('/')
        url_path = parsed_url.path

        if url_path.startswith(base_path):
            relative_path = url_path[len(base_path):].lstrip('/')
        else:
            relative_path = url_path.lstrip('/')

        return self.output_dir / relative_path

    def download_file(self, url: str, local_path: Path, verbose: bool = False) -> bool:
        """Download a single file with retry logic"""
        # Check if file already exists
        if self.skip_existing and local_path.exists():
            if verbose:
                print(f"  Skipping (exists): {local_path.relative_to(self.output_dir)}")
            self.files_skipped += 1
            return True

        # Create parent directories
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Try downloading with retries
        for attempt in range(self.max_retries):
            try:
                if verbose:
                    print(f"  Downloading: {local_path.relative_to(self.output_dir)} (attempt {attempt + 1}/{self.max_retries})")

                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                # Get file size
                total_size = int(response.headers.get('content-length', 0))

                # Download with progress
                downloaded = 0
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Show progress for large files
                            if total_size > 1024 * 1024 and verbose:  # > 1MB
                                percent = (downloaded / total_size) * 100
                                print(f"\r    Progress: {percent:.1f}% ({self.format_size(downloaded)}/{self.format_size(total_size)})",
                                      end='', flush=True)

                if total_size > 1024 * 1024 and verbose:
                    print()  # New line after progress

                self.files_downloaded += 1
                self.total_bytes += downloaded

                if verbose:
                    print(f"  ✓ Downloaded: {local_path.relative_to(self.output_dir)} ({self.format_size(downloaded)})")

                return True

            except Exception as e:
                if attempt < self.max_retries - 1:
                    if verbose:
                        print(f"  ⚠ Error (retrying): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"  ✗ Failed after {self.max_retries} attempts: {local_path.relative_to(self.output_dir)} - {e}")
                    self.failed_downloads.append((url, str(e)))
                    return False

        return False

    def parse_directory_listing(self, html_content: str, base_url: str) -> Tuple[list, list]:
        """Parse HTML directory listing - returns (files, directories)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        files = []
        directories = []

        # Look for pre-formatted text (Apache-style listings)
        pre_tags = soup.find_all('pre')
        if pre_tags:
            lines = str(pre_tags[0]).split('\n')

            for line in lines:
                # Skip header lines, hr tags, and parent directory
                if '<hr>' in line or 'Parent Directory' in line or not '<a href=' in line:
                    continue

                # Parse the line
                line_soup = BeautifulSoup(line, 'html.parser')
                link = line_soup.find('a')

                if not link:
                    continue

                href = link.get('href', '')
                filename = link.get_text().strip()

                # Skip sorting links
                if href.startswith('?'):
                    continue

                # Build full URL
                full_url = urljoin(base_url, href)

                # Check if it's a directory
                img = line_soup.find('img')
                is_dir = False
                if img:
                    alt_text = img.get('alt', '')
                    if '[DIR]' in alt_text or 'folder' in alt_text.lower():
                        is_dir = True

                if href.endswith('/') or filename.endswith('/'):
                    is_dir = True

                if is_dir:
                    directories.append(full_url)
                else:
                    files.append((full_url, filename))

            return files, directories

        # Fallback: parse links from any HTML
        all_links = soup.find_all('a')
        for link in all_links:
            href = link.get('href', '')

            # Skip special links
            if not href or href.startswith('?') or href.startswith('#') or href == '../':
                continue

            full_url = urljoin(base_url, href)

            # Only process URLs under the base URL
            if not full_url.startswith(base_url.rstrip('/').rsplit('/', 1)[0]):
                continue

            filename = link.get_text().strip()

            if href.endswith('/'):
                directories.append(full_url)
            else:
                files.append((full_url, filename))

        return files, directories

    def download_directory_recursive(self, url: str, depth: int = 0,
                                    max_depth: int = 20, verbose: bool = False) -> None:
        """Recursively download directory contents"""
        # Prevent infinite loops
        if url in self.visited_urls:
            return

        self.visited_urls.add(url)

        if depth > max_depth:
            print(f"{'  ' * depth}⚠ Max depth reached, skipping: {url}")
            return

        indent = '  ' * depth
        print(f"{indent}📁 Scanning: {url}")

        try:
            # Get directory listing
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            files, directories = self.parse_directory_listing(response.text, url)

            print(f"{indent}   Found {len(files)} files and {len(directories)} subdirectories")

            # Download all files in current directory
            for file_url, filename in files:
                self.total_files += 1
                local_path = self.get_local_path(file_url)

                if not verbose:
                    print(f"\rProgress: {self.files_downloaded + self.files_skipped}/{self.total_files} files, "
                          f"{self.format_size(self.total_bytes)} downloaded", end='', flush=True)

                self.download_file(file_url, local_path, verbose)

                if self.delay > 0:
                    time.sleep(self.delay)

            if not verbose:
                print()  # New line after progress

            # Recursively process subdirectories
            for subdir_url in directories:
                if self.delay > 0:
                    time.sleep(self.delay)

                self.download_directory_recursive(subdir_url, depth + 1, max_depth, verbose)

        except Exception as e:
            print(f"{indent}✗ Error accessing directory: {e}")

    def download(self, url: str, max_depth: int = 20, verbose: bool = False) -> None:
        """Start the download process"""
        print("=" * 70)
        print("Recursive Directory Downloader")
        print("=" * 70)
        print(f"Source URL: {url}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"Skip existing files: {self.skip_existing}")
        print(f"Request delay: {self.delay}s")
        print(f"Max retries: {self.max_retries}")
        print(f"Max depth: {max_depth}")
        print("=" * 70)

        start_time = time.time()

        # Ensure URL ends with /
        if not url.endswith('/'):
            url += '/'

        # Store the base URL for path calculations
        self.base_url = url

        # Start recursive download
        self.download_directory_recursive(url, max_depth=max_depth, verbose=verbose)

        elapsed = time.time() - start_time

        # Print summary
        print("\n" + "=" * 70)
        print("Download Complete!")
        print("=" * 70)
        print(f"Total files found: {self.total_files}")
        print(f"Files downloaded: {self.files_downloaded}")
        print(f"Files skipped (already exist): {self.files_skipped}")
        print(f"Total data downloaded: {self.format_size(self.total_bytes)}")
        print(f"Time elapsed: {elapsed:.1f} seconds")

        if self.total_bytes > 0 and elapsed > 0:
            speed = self.total_bytes / elapsed
            print(f"Average speed: {self.format_size(speed)}/s")

        if self.failed_downloads:
            print(f"\n⚠ Failed downloads: {len(self.failed_downloads)}")
            for url, error in self.failed_downloads[:10]:
                print(f"  - {url}: {error}")
            if len(self.failed_downloads) > 10:
                print(f"  ... and {len(self.failed_downloads) - 10} more")

        print(f"\nFiles saved to: {self.output_dir.absolute()}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Recursively download all files from an HTTP/FTP directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download entire release directory
  python downloader.py https://fungidb.org/common/downloads/release-68/

  # Download with verbose output
  python downloader.py https://fungidb.org/common/downloads/release-68/ --verbose

  # Download to specific directory
  python downloader.py https://example.com/files/ --output-dir ./my_files

  # Download without delay (faster but less polite)
  python downloader.py https://example.com/files/ --delay 0

  # Resume previous download (skip existing files)
  python downloader.py https://fungidb.org/common/downloads/release-68/ --skip-existing
        """
    )

    parser.add_argument('url', help='Base URL to download from')
    parser.add_argument('-o', '--output-dir', default='downloads',
                       help='Output directory (default: downloads)')
    parser.add_argument('-d', '--delay', type=float, default=0.05,
                       help='Delay between requests in seconds (default: 0.05)')
    parser.add_argument('-r', '--max-retries', type=int, default=3,
                       help='Maximum number of retry attempts (default: 3)')
    parser.add_argument('--max-depth', type=int, default=20,
                       help='Maximum recursion depth (default: 20)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed progress for each file')
    parser.add_argument('--no-skip-existing', action='store_true',
                       help='Re-download files even if they exist')

    args = parser.parse_args()

    downloader = RecursiveDownloader(
        output_dir=args.output_dir,
        delay=args.delay,
        max_retries=args.max_retries,
        skip_existing=not args.no_skip_existing
    )

    try:
        downloader.download(args.url, max_depth=args.max_depth, verbose=args.verbose)
    except KeyboardInterrupt:
        print("\n\n⚠ Download interrupted by user")
        print(f"Progress: {downloader.files_downloaded}/{downloader.total_files} files downloaded")
        print(f"You can resume by running the script again (existing files will be skipped)")
        sys.exit(1)


if __name__ == "__main__":
    main()