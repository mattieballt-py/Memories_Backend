"""Quick test script for the SHARP web API.

Usage:
    python test_web_api.py --image photo.jpg --api-url https://your-app.modal.run
"""

import argparse
import sys
from pathlib import Path

import requests


def test_health(api_url: str):
    """Test the health endpoint."""
    print(f"Testing health endpoint: {api_url}/health")
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        data = response.json()
        print("✓ Health check passed:")
        print(f"  Status: {data['status']}")
        print(f"  CUDA available: {data['cuda_available']}")
        print(f"  Device: {data['device']}")
        print(f"  AWS configured: {data['aws_configured']}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_splat(api_url: str, image_path: Path, f_px: float = None):
    """Test the /splat endpoint with an image."""
    print(f"\nTesting /splat endpoint with image: {image_path}")

    if not image_path.exists():
        print(f"✗ Error: Image file not found: {image_path}")
        return False

    try:
        with open(image_path, "rb") as f:
            files = {"file": (image_path.name, f, "image/jpeg")}
            data = {}
            if f_px is not None:
                data["f_px"] = f_px

            print(f"Uploading image ({image_path.stat().st_size} bytes)...")
            response = requests.post(
                f"{api_url}/splat",
                files=files,
                data=data,
                timeout=120  # 2 minutes timeout for first request
            )

        if response.ok:
            result = response.json()
            print("✓ Success!")
            print(f"  PLY URL: {result['ply_url']}")
            print(f"  Original filename: {result['metadata']['original_filename']}")
            print(f"  PLY size: {result['metadata']['ply_size_bytes'] / 1024 / 1024:.2f} MB")
            print(f"  Focal length: {result['metadata']['focal_length']}")

            # Test downloading the PLY file
            print("\nTesting PLY file download...")
            ply_response = requests.get(result['ply_url'], timeout=30)
            if ply_response.ok:
                output_path = Path(f"test_output_{image_path.stem}.ply")
                with open(output_path, "wb") as f:
                    f.write(ply_response.content)
                print(f"✓ PLY file downloaded successfully: {output_path}")
                print(f"  Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
            else:
                print(f"✗ Failed to download PLY file: {ply_response.status_code}")

            return True
        else:
            print(f"✗ Request failed: {response.status_code}")
            print(f"  Error: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test the SHARP Web API")
    parser.add_argument(
        "--api-url",
        type=str,
        required=True,
        help="API URL (e.g., https://your-username--sharp-web-api-fastapi-app.modal.run)"
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Path to test image (optional, only for /splat test)"
    )
    parser.add_argument(
        "--f-px",
        type=float,
        help="Focal length in pixels (optional)"
    )

    args = parser.parse_args()

    # Remove trailing slash from API URL
    api_url = args.api_url.rstrip("/")

    print("=" * 60)
    print("SHARP Web API Test")
    print("=" * 60)

    # Test health endpoint
    health_ok = test_health(api_url)

    if not health_ok:
        print("\n⚠ Health check failed. API may not be deployed or accessible.")
        sys.exit(1)

    # Test splat endpoint if image provided
    if args.image:
        splat_ok = test_splat(api_url, args.image, args.f_px)
        if splat_ok:
            print("\n✓ All tests passed!")
        else:
            print("\n✗ /splat test failed")
            sys.exit(1)
    else:
        print("\n✓ Health check passed!")
        print("\nTo test the /splat endpoint, run:")
        print(f"  python test_web_api.py --api-url {api_url} --image /path/to/image.jpg")


if __name__ == "__main__":
    main()
