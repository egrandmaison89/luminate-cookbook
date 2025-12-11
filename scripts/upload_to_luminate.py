#!/usr/bin/env python3
"""
Luminate Online Image Upload Automation

This script automates uploading images to the Luminate Online Image Library:
1. Logs into Luminate Online
2. Navigates to the Image Library
3. Uploads each image from the resized folder
4. Generates a file with URLs for all uploaded images

Usage: python upload_to_luminate.py
"""

import os
import sys
import glob
from dotenv import load_dotenv

# Add parent directory to path to import from lib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.luminate_uploader_lib import upload_images_batch, generate_url

# Load environment variables from .env file
load_dotenv()

# Configuration
RESIZED_DIR = "resized"
OUTPUT_FILE = "uploaded_urls.txt"

# Credentials from environment variables
USERNAME = os.getenv("LUMINATE_USERNAME")
PASSWORD = os.getenv("LUMINATE_PASSWORD")


def get_image_files(directory):
    """Get all image files from the resized directory."""
    pattern = os.path.join(directory, "*.jpg")
    files = sorted(glob.glob(pattern))
    return files


def generate_urls_file(uploaded_files, output_path):
    """Generate a file with URLs for all uploaded images."""
    print(f"\nGenerating URLs file: {output_path}")
    
    with open(output_path, 'w') as f:
        for filename in uploaded_files:
            url = generate_url(filename)
            f.write(url + '\n')
    
    print(f"Saved {len(uploaded_files)} URLs to {output_path}")


def progress_callback(current, total, filename, status):
    """Progress callback for CLI output."""
    if status == "info":
        print(f"\n{filename}")
    elif status == "uploading":
        print(f"\n[{current}/{total}] Uploading: {filename}")
    elif status == "success":
        print(f"  ✓ Uploaded: {filename}")
    elif status == "error":
        print(f"  ✗ Failed: {filename}")


def main():
    print("=" * 70)
    print("LUMINATE ONLINE IMAGE UPLOAD AUTOMATION")
    print("=" * 70)
    
    # Check for credentials
    if not USERNAME or not PASSWORD:
        print("\nERROR: Missing credentials!")
        print("Please create a .env file with:")
        print("  LUMINATE_USERNAME=your_username")
        print("  LUMINATE_PASSWORD=your_password")
        return
    
    # Get all images to upload
    image_files = get_image_files(RESIZED_DIR)
    
    if not image_files:
        print(f"\nERROR: No images found in '{RESIZED_DIR}' directory")
        return
    
    print(f"\nFound {len(image_files)} images to upload")
    
    # Upload images using the library
    print("\nStarting upload process...")
    results = upload_images_batch(USERNAME, PASSWORD, image_files, progress_callback)
    
    # Print summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"\nSuccessfully uploaded: {len(results['successful'])}/{len(image_files)} images")
    
    if results['failed']:
        print(f"\nFailed uploads: {len(results['failed'])}")
        for filename, error in results['failed']:
            print(f"  ✗ {filename}: {error}")
    
    # Generate URLs file
    if results['successful']:
        generate_urls_file(results['successful'], OUTPUT_FILE)
        
        print(f"\n{'=' * 70}")
        print("GENERATED URLs:")
        print("=" * 70)
        for url in results['urls']:
            print(f"  {url}")


if __name__ == "__main__":
    main()
