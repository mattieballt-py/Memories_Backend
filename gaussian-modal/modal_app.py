"""Modal deployment for SHARP view synthesis model.

This module provides a Modal app for running SHARP inference on GPU.
"""

import io
from pathlib import Path

import modal

# Create a Modal app
app = modal.App("sharp-view-synthesis")

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
    )
    .copy_local_dir("src/sharp", "/root/sharp")
)

# Create a volume for caching the model checkpoint
model_cache = modal.Volume.from_name("sharp-model-cache", create_if_missing=True)

MODEL_CACHE_PATH = "/cache"
DEFAULT_MODEL_URL = "https://ml-site.cdn-apple.com/models/sharp/sharp_2572gikvuh.pt"


@app.function(
    image=image,
    gpu=modal.gpu.A100(count=1),  # Use A100 GPU
    volumes={MODEL_CACHE_PATH: model_cache},
    timeout=600,  # 10 minute timeout
    allow_concurrent_inputs=10,
)
def predict(image_bytes: bytes, f_px: float = None) -> dict:
    """Predict 3D Gaussians from an input image.

    Args:
        image_bytes: Input image as bytes
        f_px: Focal length in pixels (optional, will be estimated if not provided)

    Returns:
        Dictionary containing the Gaussian parameters and metadata
    """
    import sys
    sys.path.insert(0, "/root")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image

    from sharp.models import PredictorParams, create_predictor
    from sharp.utils import io as sharp_io
    from sharp.utils.gaussians import unproject_gaussians

    # Load model
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

    # Initialize model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    gaussian_predictor = create_predictor(PredictorParams())
    gaussian_predictor.load_state_dict(state_dict)
    gaussian_predictor.eval()
    gaussian_predictor.to(device)

    # Load and process image
    image_pil = Image.open(io.BytesIO(image_bytes))
    image = np.array(image_pil.convert("RGB"))
    height, width = image.shape[:2]

    # Estimate focal length if not provided
    if f_px is None:
        # Default estimation: assume 50mm equivalent focal length
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

    # Predict Gaussians in the NDC space
    with torch.no_grad():
        gaussians_ndc = gaussian_predictor(image_resized_pt, disparity_factor)

    # Setup intrinsics
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

    # Convert Gaussians to metrics space
    gaussians = unproject_gaussians(
        gaussians_ndc, torch.eye(4).to(device), intrinsics_resized, internal_shape
    )

    # Convert to serializable format
    result = {
        "positions": gaussians.positions.cpu().numpy().tolist(),
        "scales": gaussians.scales.cpu().numpy().tolist(),
        "rotations": gaussians.rotations.cpu().numpy().tolist(),
        "opacities": gaussians.opacities.cpu().numpy().tolist(),
        "colors": gaussians.colors.cpu().numpy().tolist(),
        "metadata": {
            "focal_length": f_px,
            "image_size": (width, height),
            "num_gaussians": len(gaussians.positions),
        }
    }

    return result


@app.function(
    image=image,
    gpu=modal.gpu.A100(count=1),
    volumes={MODEL_CACHE_PATH: model_cache},
    timeout=600,
)
def predict_and_save_ply(image_bytes: bytes, f_px: float = None) -> bytes:
    """Predict 3D Gaussians and return as PLY file bytes.

    Args:
        image_bytes: Input image as bytes
        f_px: Focal length in pixels (optional, will be estimated if not provided)

    Returns:
        PLY file as bytes
    """
    import sys
    sys.path.insert(0, "/root")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image

    from sharp.models import PredictorParams, create_predictor
    from sharp.utils.gaussians import unproject_gaussians, save_ply

    # Load model
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

    # Initialize model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    gaussian_predictor = create_predictor(PredictorParams())
    gaussian_predictor.load_state_dict(state_dict)
    gaussian_predictor.eval()
    gaussian_predictor.to(device)

    # Load and process image
    image_pil = Image.open(io.BytesIO(image_bytes))
    image = np.array(image_pil.convert("RGB"))
    height, width = image.shape[:2]

    # Estimate focal length if not provided
    if f_px is None:
        f_px = max(width, height) * 1.2

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
        gaussians_ndc = gaussian_predictor(image_resized_pt, disparity_factor)

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
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".ply", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        save_ply(gaussians, f_px, (height, width), tmp_path)

        with open(tmp_path, "rb") as f:
            ply_bytes = f.read()

        tmp_path.unlink()

    return ply_bytes


@app.local_entrypoint()
def main(image_path: str, output_path: str = None, f_px: float = None):
    """Local entrypoint for testing the Modal deployment.

    Usage:
        modal run modal_app.py --image-path /path/to/image.jpg --output-path /path/to/output.ply
    """
    from pathlib import Path

    # Read image
    image_path = Path(image_path)
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print(f"Processing {image_path.name}...")

    # Call the function
    ply_bytes = predict_and_save_ply.remote(image_bytes, f_px)

    # Save output
    if output_path is None:
        output_path = image_path.with_suffix(".ply")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(ply_bytes)

    print(f"Saved PLY to {output_path}")
