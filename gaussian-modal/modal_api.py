"""Modal FastAPI web endpoint for SHARP view synthesis model.

This module provides a web API for the SHARP model deployed on Modal.
"""

import io
from pathlib import Path
from typing import Optional

import modal
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response, JSONResponse

# Create a Modal app
app = modal.App("sharp-api")

# Define the image with all dependencies
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
    )
    .add_local_dir("src/sharp", "/root/sharp")
)

# Create a volume for caching the model checkpoint
model_cache = modal.Volume.from_name("sharp-model-cache", create_if_missing=True)

MODEL_CACHE_PATH = "/cache"
DEFAULT_MODEL_URL = "https://ml-site.cdn-apple.com/models/sharp/sharp_2572gikvuh.pt"

web_app = FastAPI(
    title="SHARP View Synthesis API",
    description="Generate 3D Gaussian representations from single images",
    version="1.0.0"
)


def load_model():
    """Load the SHARP model."""
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


def process_image(image_bytes: bytes, f_px: Optional[float], predictor, device):
    """Process an image and return Gaussians."""
    import sys
    sys.path.insert(0, "/root")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from sharp.utils.gaussians import unproject_gaussians

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

    return gaussians, f_px, (height, width)


@web_app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "SHARP View Synthesis API",
        "version": "1.0.0",
        "endpoints": {
            "/predict": "POST - Get Gaussian parameters as JSON",
            "/predict/ply": "POST - Get 3D Gaussians as PLY file",
            "/health": "GET - Health check"
        }
    }


@web_app.get("/health")
async def health():
    """Health check endpoint."""
    import torch
    return {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }


@web_app.post("/predict")
async def predict_json(
    file: UploadFile = File(...),
    f_px: Optional[float] = Form(None)
):
    """Predict 3D Gaussians and return as JSON.

    Args:
        file: Input image file
        f_px: Focal length in pixels (optional)

    Returns:
        JSON with Gaussian parameters and metadata
    """
    try:
        # Read image
        image_bytes = await file.read()

        # Load model
        predictor, device = load_model()

        # Process
        gaussians, focal_length, image_size = process_image(
            image_bytes, f_px, predictor, device
        )

        # Convert to JSON
        result = {
            "positions": gaussians.positions.cpu().numpy().tolist(),
            "scales": gaussians.scales.cpu().numpy().tolist(),
            "rotations": gaussians.rotations.cpu().numpy().tolist(),
            "opacities": gaussians.opacities.cpu().numpy().tolist(),
            "colors": gaussians.colors.cpu().numpy().tolist(),
            "metadata": {
                "focal_length": focal_length,
                "image_size": image_size,
                "num_gaussians": len(gaussians.positions),
            }
        }

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@web_app.post("/predict/ply")
async def predict_ply(
    file: UploadFile = File(...),
    f_px: Optional[float] = Form(None)
):
    """Predict 3D Gaussians and return as PLY file.

    Args:
        file: Input image file
        f_px: Focal length in pixels (optional)

    Returns:
        PLY file
    """
    import sys
    sys.path.insert(0, "/root")

    try:
        # Read image
        image_bytes = await file.read()

        # Load model
        predictor, device = load_model()

        # Process
        gaussians, focal_length, image_size = process_image(
            image_bytes, f_px, predictor, device
        )

        # Save to temporary file
        import tempfile
        from sharp.utils.gaussians import save_ply

        with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            save_ply(gaussians, focal_length, image_size, tmp_path)

            with open(tmp_path, "rb") as f:
                ply_bytes = f.read()

            tmp_path.unlink()

        return Response(
            content=ply_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={file.filename.rsplit('.', 1)[0]}.ply"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.function(
    image=image,
    gpu=modal.gpu.A100(count=1),
    volumes={MODEL_CACHE_PATH: model_cache},
    timeout=600,
    allow_concurrent_inputs=10,
    container_idle_timeout=300,  # Keep container warm for 5 minutes
)
@modal.asgi_app()
def fastapi_app():
    """Deploy the FastAPI app on Modal."""
    return web_app
