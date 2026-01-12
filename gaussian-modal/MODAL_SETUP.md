# Modal GPU Setup for SHARP View Synthesis

This guide explains how to deploy and use the SHARP model on Modal GPUs.

## Prerequisites

1. **Install Modal**
   ```bash
   pip install modal
   ```

2. **Set up Modal account**
   ```bash
   modal setup
   ```
   This will open a browser to authenticate with Modal.

3. **Create Modal token**
   ```bash
   modal token new
   ```

## Deployment Options

This repository includes two Modal deployment options:

### 1. Function-based API (`modal_app.py`)

Simple function-based deployment for programmatic access.

**Deploy:**
```bash
cd gaussian-modal
modal deploy modal_app.py
```

**Test locally:**
```bash
modal run modal_app.py --image-path /path/to/image.jpg --output-path output.ply
```

**Use in Python:**
```python
import modal

# Connect to the deployed app
predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

# Read image
with open("image.jpg", "rb") as f:
    image_bytes = f.read()

# Call the function
ply_bytes = predict_fn.remote(image_bytes, f_px=1200.0)

# Save result
with open("output.ply", "wb") as f:
    f.write(ply_bytes)
```

### 2. FastAPI Web Endpoint (`modal_api.py`)

Full REST API with web endpoints for HTTP access.

**Deploy:**
```bash
cd gaussian-modal
modal deploy modal_api.py
```

This will output a URL like: `https://your-username--sharp-api-fastapi-app.modal.run`

**API Endpoints:**

- `GET /` - API information
- `GET /health` - Health check
- `POST /predict` - Get Gaussian parameters as JSON
- `POST /predict/ply` - Get 3D Gaussians as PLY file

**Test with curl:**
```bash
# Get PLY file
curl -X POST "https://your-username--sharp-api-fastapi-app.modal.run/predict/ply" \
  -F "file=@image.jpg" \
  -F "f_px=1200" \
  -o output.ply

# Get JSON response
curl -X POST "https://your-username--sharp-api-fastapi-app.modal.run/predict" \
  -F "file=@image.jpg" \
  -F "f_px=1200"
```

**Test with Python:**
```python
import requests

url = "https://your-username--sharp-api-fastapi-app.modal.run/predict/ply"

with open("image.jpg", "rb") as f:
    files = {"file": f}
    data = {"f_px": 1200.0}  # Optional
    response = requests.post(url, files=files, data=data)

with open("output.ply", "wb") as f:
    f.write(response.content)
```

## Features

### GPU Configuration

Both deployments use NVIDIA A100 GPUs by default. You can modify the GPU type:

```python
@app.function(
    gpu=modal.gpu.A10G(count=1),  # Use A10G instead
    # or
    gpu=modal.gpu.A100(count=1, size="40GB"),  # Specify size
    # or
    gpu=modal.gpu.H100(count=1),  # Use H100
)
```

Available GPU options:
- `modal.gpu.T4()` - Budget option
- `modal.gpu.A10G()` - Good performance
- `modal.gpu.A100()` - High performance (default)
- `modal.gpu.H100()` - Maximum performance

### Model Caching

The model checkpoint (2.5GB) is automatically:
1. Downloaded on first run
2. Cached in a Modal Volume (`sharp-model-cache`)
3. Reused across all subsequent calls

This means:
- First run: ~30 seconds (download + inference)
- Subsequent runs: ~2-5 seconds (inference only)

### Container Idle Timeout

The FastAPI endpoint keeps containers warm for 5 minutes (`container_idle_timeout=300`). This means:
- Fast response times for requests within 5 minutes
- Automatic scale-down when idle
- No charges when not in use

Adjust this based on your needs:
```python
container_idle_timeout=300,  # 5 minutes
# or
container_idle_timeout=600,  # 10 minutes
```

### Concurrent Requests

The functions support up to 10 concurrent requests:
```python
allow_concurrent_inputs=10,
```

Increase this if you need higher concurrency:
```python
allow_concurrent_inputs=20,
```

## Parameters

### Input Parameters

- `image_bytes` (required): Input image as bytes (JPEG, PNG, etc.)
- `f_px` (optional): Focal length in pixels
  - If not provided, estimated as `max(width, height) * 1.2`
  - Typically between 0.8-1.5x the larger image dimension
  - Use EXIF data if available for best results

### Output Formats

**PLY Format** (`predict_and_save_ply` / `/predict/ply`):
- Standard 3D Gaussian Splatting format
- Compatible with various 3DGS renderers
- OpenCV coordinate convention (x right, y down, z forward)

**JSON Format** (`predict` / `/predict`):
- `positions`: 3D positions of Gaussians [N, 3]
- `scales`: Scale parameters [N, 3]
- `rotations`: Rotation quaternions [N, 4]
- `opacities`: Opacity values [N, 1]
- `colors`: RGB colors [N, 3]
- `metadata`: Image info and statistics

## Cost Considerations

Modal pricing (as of 2024):
- A100 40GB: ~$1.10/hour compute
- Storage (volumes): ~$0.15/GB-month
- Network egress: $0.10/GB

Typical costs per inference:
- First run: ~$0.01 (includes download)
- Subsequent runs: ~$0.001-0.002

For production use, consider:
1. Using cheaper GPUs (A10G) for faster inference
2. Batching requests when possible
3. Adjusting `container_idle_timeout` based on usage patterns

## Monitoring

View logs and monitor your deployments:
```bash
modal app logs sharp-view-synthesis
# or
modal app logs sharp-api
```

View running apps:
```bash
modal app list
```

## Troubleshooting

### Error: "Module not found"
Make sure you're running from the `gaussian-modal` directory, which contains the `src/sharp` folder.

### Error: "CUDA out of memory"
Try using a larger GPU:
```python
gpu=modal.gpu.A100(size="80GB")
```

### Slow first request
The first request downloads the model (~2.5GB). Subsequent requests are much faster due to caching.

### Authentication errors
Re-run Modal setup:
```bash
modal setup
modal token new
```

## Advanced Usage

### Custom Image Preprocessing

You can modify the preprocessing in the functions:

```python
# Example: Add image normalization
def preprocess_image(image_bytes):
    from PIL import Image
    import numpy as np

    image_pil = Image.open(io.BytesIO(image_bytes))
    image = np.array(image_pil.convert("RGB"))

    # Add your preprocessing here
    # e.g., normalize, resize, etc.

    return image
```

### Batch Processing

For processing multiple images:

```python
import modal

predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]

# Process in parallel
results = []
for path in image_paths:
    with open(path, "rb") as f:
        image_bytes = f.read()

    # .remote() is non-blocking, so this runs in parallel
    result = predict_fn.remote(image_bytes)
    results.append(result)

# Wait for all results
ply_files = [r for r in results]
```

### Using with Different Model Checkpoints

To use a different checkpoint:

1. Modify the `DEFAULT_MODEL_URL` in the code
2. Or upload your checkpoint to Modal:

```python
checkpoint_volume = modal.Volume.from_name("my-checkpoints", create_if_missing=True)

# Upload checkpoint
with checkpoint_volume.batch_upload() as batch:
    batch.put_file("local_checkpoint.pt", "checkpoint.pt")
```

## Next Steps

1. Deploy one of the options
2. Test with your images
3. Integrate into your application
4. Monitor usage and adjust GPU settings as needed

For more information:
- [Modal Documentation](https://modal.com/docs)
- [SHARP Paper](https://arxiv.org/abs/2512.10685)
- [SHARP Project Page](https://apple.github.io/ml-sharp/)
