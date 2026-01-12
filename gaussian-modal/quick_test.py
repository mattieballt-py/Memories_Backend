#!/usr/bin/env python3
"""Quick test script for the deployed SHARP API."""

import sys
from pathlib import Path

# Check if we have an image path argument
if len(sys.argv) < 2:
    print("Usage: python quick_test.py /path/to/image.jpg")
    print("\nExample:")
    print("  python quick_test.py ~/Desktop/my_photo.jpg")
    sys.exit(1)

image_path = Path(sys.argv[1])

if not image_path.exists():
    print(f"Error: Image not found at {image_path}")
    sys.exit(1)

print(f"Testing SHARP API with image: {image_path}")

# Test 1: Health check
print("\n1. Testing health endpoint...")
import requests

API_URL = "https://mattieballt-py--sharp-api-fastapi-app.modal.run"

try:
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")
    sys.exit(1)

# Test 2: Get Gaussian JSON
print("\n2. Testing prediction endpoint (JSON)...")
try:
    with open(image_path, "rb") as f:
        files = {"file": ("image.jpg", f, "image/jpeg")}
        response = requests.post(f"{API_URL}/predict", files=files)

    if response.status_code == 200:
        result = response.json()
        print(f"   Success! Got {result['metadata']['num_gaussians']} Gaussians")
        print(f"   Image size: {result['metadata']['image_size']}")
        print(f"   Focal length: {result['metadata']['focal_length']:.2f}px")
    else:
        print(f"   Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Get PLY file
print("\n3. Testing PLY endpoint...")
try:
    output_path = image_path.with_suffix(".ply")

    with open(image_path, "rb") as f:
        files = {"file": ("image.jpg", f, "image/jpeg")}
        response = requests.post(f"{API_URL}/predict/ply", files=files)

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"   Success! PLY saved to: {output_path}")
        print(f"   File size: {len(response.content) / 1024:.2f} KB")
    else:
        print(f"   Error {response.status_code}: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n✅ All tests complete!")
