"""Example client for calling the SHARP Modal API.

This script demonstrates how to use the deployed Modal functions.
"""

import argparse
from pathlib import Path
from typing import Optional


def call_function_api(image_path: Path, output_path: Path, f_px: Optional[float] = None):
    """Call the function-based API."""
    import modal

    print("Connecting to Modal function...")
    predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

    print(f"Reading image: {image_path}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print("Calling prediction function...")
    ply_bytes = predict_fn.remote(image_bytes, f_px)

    print(f"Saving PLY to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(ply_bytes)

    print("Done!")


def call_web_api(
    image_path: Path,
    output_path: Path,
    api_url: str,
    f_px: Optional[float] = None,
    output_format: str = "ply"
):
    """Call the web API endpoint."""
    import requests

    if output_format == "ply":
        endpoint = f"{api_url}/predict/ply"
    else:
        endpoint = f"{api_url}/predict"

    print(f"Calling API: {endpoint}")

    with open(image_path, "rb") as f:
        files = {"file": ("image.jpg", f, "image/jpeg")}
        data = {}
        if f_px is not None:
            data["f_px"] = f_px

        print(f"Uploading image: {image_path}")
        response = requests.post(endpoint, files=files, data=data)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "ply":
        print(f"Saving PLY to: {output_path}")
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        import json
        print(f"Saving JSON to: {output_path}")
        with open(output_path, "w") as f:
            json.dump(response.json(), f, indent=2)

    print("Done!")


def batch_process(
    image_dir: Path,
    output_dir: Path,
    api_type: str = "function",
    api_url: Optional[str] = None,
    f_px: Optional[float] = None
):
    """Process all images in a directory."""
    import modal

    # Find all images
    extensions = [".jpg", ".jpeg", ".png", ".webp", ".heic"]
    image_paths = []
    for ext in extensions:
        image_paths.extend(list(image_dir.glob(f"**/*{ext}")))
        image_paths.extend(list(image_dir.glob(f"**/*{ext.upper()}")))

    if not image_paths:
        print(f"No images found in {image_dir}")
        return

    print(f"Found {len(image_paths)} images")

    if api_type == "function":
        print("Using function API for batch processing...")
        predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

        # Process in parallel
        results = []
        for image_path in image_paths:
            print(f"Submitting: {image_path.name}")
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # .remote() is non-blocking
            result = predict_fn.remote(image_bytes, f_px)
            results.append((image_path, result))

        # Wait for results and save
        output_dir.mkdir(parents=True, exist_ok=True)
        for image_path, result in results:
            output_path = output_dir / f"{image_path.stem}.ply"
            print(f"Saving: {output_path.name}")
            with open(output_path, "wb") as f:
                f.write(result)

    else:
        print("Using web API for batch processing...")
        output_dir.mkdir(parents=True, exist_ok=True)
        for image_path in image_paths:
            output_path = output_dir / f"{image_path.stem}.ply"
            print(f"Processing: {image_path.name}")
            call_web_api(image_path, output_path, api_url, f_px)

    print("Batch processing complete!")


def main():
    parser = argparse.ArgumentParser(description="SHARP Modal API Client")
    parser.add_argument("--image", type=Path, help="Input image path")
    parser.add_argument("--image-dir", type=Path, help="Input directory for batch processing")
    parser.add_argument("--output", type=Path, help="Output path")
    parser.add_argument("--output-dir", type=Path, help="Output directory for batch processing")
    parser.add_argument(
        "--api-type",
        choices=["function", "web"],
        default="function",
        help="API type to use"
    )
    parser.add_argument("--api-url", type=str, help="Web API URL (required for --api-type web)")
    parser.add_argument("--f-px", type=float, help="Focal length in pixels (optional)")
    parser.add_argument(
        "--format",
        choices=["ply", "json"],
        default="ply",
        help="Output format (only for web API)"
    )

    args = parser.parse_args()

    # Batch processing
    if args.image_dir:
        if not args.output_dir:
            args.output_dir = args.image_dir / "gaussians"
        batch_process(args.image_dir, args.output_dir, args.api_type, args.api_url, args.f_px)
        return

    # Single image processing
    if not args.image:
        parser.error("Either --image or --image-dir is required")

    if not args.output:
        args.output = args.image.with_suffix(".ply" if args.format == "ply" else ".json")

    if args.api_type == "function":
        if args.format == "json":
            print("Warning: JSON format not supported with function API, using PLY")
        call_function_api(args.image, args.output, args.f_px)
    else:
        if not args.api_url:
            parser.error("--api-url is required when using --api-type web")
        call_web_api(args.image, args.output, args.api_url, args.f_px, args.format)


if __name__ == "__main__":
    main()
