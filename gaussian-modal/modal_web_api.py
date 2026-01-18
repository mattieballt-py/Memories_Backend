"""Modal FastAPI web endpoint for SHARP view synthesis model with S3 upload.

This module provides an HTTP endpoint that:
1. Accepts image uploads from a React frontend
2. Generates 3D Gaussian PLY files using the SHARP model
3. Uploads PLY files to S3 and returns a public URL

The existing CLI/batch API in modal_app.py remains unchanged.
"""

import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import modal
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create a Modal app
app = modal.App("sharp-web-api")

# Define the image with all dependencies (including boto3 for S3)
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git", "wget")
    .pip_install(
        "click",
        "gsplat==1.5.3",
        "imageio[ffmpeg]",
        "matplotlib",
        "pillow-heif",
        "plyfile",
        "scipy",
        "timm",
        "torch==2.8.0",
        "torchvision==0.23.0",
        "numpy",
        "requests",
        "fastapi[standard]",
        "python-multipart",
        "boto3",  # For S3 upload
    )
    .copy_local_dir("src/sharp", "/root/sharp")
)

# Create a volume for caching the model checkpoint
model_cache = modal.Volume.from_name("sharp-model-cache", create_if_missing=True)

MODEL_CACHE_PATH = "/cache"
DEFAULT_MODEL_URL = "https://ml-site.cdn-apple.com/models/sharp/sharp_2572gikvuh.pt"

# Create FastAPI app
web_app = FastAPI(
    title="SHARP View Synthesis Web API",
    description="Generate 3D Gaussian representations from single images and upload to S3",
    version="1.0.0"
)

# Add CORS middleware to allow React frontend to call this API
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_model():
    """Load the SHARP model (cached across requests)."""
    import sys
    sys.path.insert(0, "/root")

    import torch
    from sharp.models import PredictorParams, create_predictor

    checkpoint_path = Path(MODEL_CACHE_PATH) / "sharp_2572gikvuh.pt"

    if not checkpoint_path.exists():
        print(f"Downloading model from {DEFAULT_MODEL_URL}")
        state_dict = torch.hub.load_state_dict_from_url(
            DEFAULT_MODEL_URL,
            progress=True,
            model_dir=MODEL_CACHE_PATH
        )
        torch.save(state_dict, checkpoint_path)
        model_cache.commit()
    else:
        print(f"Loading cached model from {checkpoint_path}")
        state_dict = torch.load(checkpoint_path, weights_only=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    gaussian_predictor = create_predictor(PredictorParams())
    gaussian_predictor.load_state_dict(state_dict)
    gaussian_predictor.eval()
    gaussian_predictor.to(device)

    return gaussian_predictor, device


def generate_ply(image_bytes: bytes, f_px: Optional[float], predictor, device) -> bytes:
    """Generate PLY file from image bytes using the SHARP model.

    This function encapsulates the core SHARP inference logic.
    """
    import sys
    sys.path.insert(0, "/root")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from sharp.utils.gaussians import unproject_gaussians, save_ply

    # Load and process image
    image_pil = Image.open(io.BytesIO(image_bytes))
    image = np.array(image_pil.convert("RGB"))
    height, width = image.shape[:2]

    # Estimate focal length if not provided
    if f_px is None:
        f_px = max(width, height) * 1.2

    print(f"Image size: {width}x{height}, focal length: {f_px}")

    # Run inference
    internal_shape = (1536, 1536)

    image_pt = torch.from_numpy(image.copy()).float().to(device).permute(2, 0, 1) / 255.0
    disparity_factor = torch.tensor([f_px / width]).float().to(device)

    image_resized_pt = F.interpolate(
        image_pt[None],
        size=(internal_shape[1], internal_shape[0]),
        mode="bilinear",
        align_corners=True,
    )

    with torch.no_grad():
        gaussians_ndc = predictor(image_resized_pt, disparity_factor)

    intrinsics = (
        torch.tensor(
            [
                [f_px, 0, width / 2, 0],
                [0, f_px, height / 2, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]
        )
        .float()
        .to(device)
    )
    intrinsics_resized = intrinsics.clone()
    intrinsics_resized[0] *= internal_shape[0] / width
    intrinsics_resized[1] *= internal_shape[1] / height

    gaussians = unproject_gaussians(
        gaussians_ndc, torch.eye(4).to(device), intrinsics_resized, internal_shape
    )

    # Save to temporary file and return bytes
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        save_ply(gaussians, f_px, (height, width), tmp_path)

        with open(tmp_path, "rb") as f:
            ply_bytes = f.read()

        tmp_path.unlink()

    return ply_bytes


def upload_to_s3(ply_bytes: bytes, original_filename: str) -> str:
    """Upload PLY file to S3 and return a presigned URL valid for 1 hour.

    Expects environment variables:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION
    - S3_BUCKET_NAME
    """
    import boto3
    from botocore.exceptions import ClientError

    # Get AWS credentials from environment
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    s3_bucket = os.environ.get("S3_BUCKET_NAME")

    if not all([aws_access_key, aws_secret_key, s3_bucket]):
        raise ValueError(
            "Missing AWS credentials. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME"
        )

    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    # Generate unique filename
    base_name = Path(original_filename).stem
    unique_id = uuid.uuid4().hex[:8]
    s3_key = f"ply-files/{base_name}_{unique_id}.ply"

    print(f"Uploading to S3: s3://{s3_bucket}/{s3_key}")

    try:
        # Upload file
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=ply_bytes,
            ContentType='application/octet-stream',
            # Optional: Set ACL to public-read if your bucket allows it
            # ACL='public-read'
        )

        # Generate presigned URL valid for 1 hour
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': s3_bucket,
                'Key': s3_key
            },
            ExpiresIn=3600  # 1 hour
        )

        print(f"Upload successful. URL: {presigned_url}")
        return presigned_url

    except ClientError as e:
        print(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")


@web_app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "SHARP View Synthesis Web API",
        "version": "1.0.0",
        "endpoints": {
            "/splat": "POST - Upload image, generate 3D Gaussian PLY, return public URL",
            "/health": "GET - Health check"
        },
        "usage": "POST image file to /splat with multipart/form-data field 'file'"
    }


@web_app.get("/health")
async def health():
    """Health check endpoint."""
    import torch

    # Check AWS config
    aws_configured = all([
        os.environ.get("AWS_ACCESS_KEY_ID"),
        os.environ.get("AWS_SECRET_ACCESS_KEY"),
        os.environ.get("S3_BUCKET_NAME")
    ])

    return {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "aws_configured": aws_configured
    }


@web_app.post("/splat")
async def splat_endpoint(
    file: UploadFile = File(..., description="Image file to convert to 3D"),
    f_px: Optional[float] = Form(None, description="Focal length in pixels (optional)")
):
    """Generate 3D Gaussian PLY from uploaded image and return public URL.

    Args:
        file: Image file (JPEG, PNG, HEIC, WebP)
        f_px: Optional focal length in pixels. If not provided, estimated automatically.

    Returns:
        JSON: {"ply_url": "https://...", "metadata": {...}}

    Example:
        curl -X POST -F "file=@photo.jpg" https://your-app.modal.run/splat
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Must be an image."
            )

        print(f"Received image: {file.filename}, type: {file.content_type}, focal_length: {f_px}")

        # Read image bytes
        image_bytes = await file.read()

        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        print(f"Image size: {len(image_bytes)} bytes")

        # Load model
        predictor, device = load_model()

        # Generate PLY file
        print("Generating 3D Gaussians...")
        ply_bytes = generate_ply(image_bytes, f_px, predictor, device)
        print(f"Generated PLY file: {len(ply_bytes)} bytes")

        # Upload to S3
        print("Uploading to S3...")
        ply_url = upload_to_s3(ply_bytes, file.filename or "output.ply")

        # Return response
        return JSONResponse(
            content={
                "ply_url": ply_url,
                "metadata": {
                    "original_filename": file.filename,
                    "ply_size_bytes": len(ply_bytes),
                    "focal_length": f_px
                }
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing image: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.function(
    image=image,
    gpu=modal.gpu.A100(count=1),  # Use A100 GPU for inference
    volumes={MODEL_CACHE_PATH: model_cache},
    timeout=600,
    allow_concurrent_inputs=10,
    container_idle_timeout=300,  # Keep container warm for 5 minutes
    secrets=[modal.Secret.from_name("aws-credentials")],  # Load AWS credentials from Modal secrets
)
@modal.asgi_app()
def fastapi_app():
    """Deploy the FastAPI app on Modal with GPU support."""
    return web_app
