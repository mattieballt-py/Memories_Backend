# SHARP API Usage Guide

## Your Deployed API

**URL**: `https://mattieballt-py--sharp-api-fastapi-app.modal.run`

**Endpoints**:
- `GET /` - API information
- `GET /health` - Health check
- `POST /predict` - Get Gaussian parameters as JSON
- `POST /predict/ply` - Get 3D Gaussians as PLY file

## Quick Start

### 1. Activate the virtual environment

```bash
source venv/bin/activate
```

### 2. Test the API

```bash
# Replace with your actual image path
python quick_test.py ~/Desktop/my_photo.jpg
```

This will:
- Check if the API is healthy
- Get Gaussian predictions as JSON
- Download a PLY file next to your image

### 3. Using the Example Client

#### Single Image (Web API - Recommended)
```bash
python example_client.py \
  --image ~/Desktop/my_photo.jpg \
  --api-type web \
  --api-url https://mattieballt-py--sharp-api-fastapi-app.modal.run
```

#### Batch Process a Directory
```bash
python example_client.py \
  --image-dir ~/Desktop/my_photos \
  --output-dir ~/Desktop/my_photos/gaussians \
  --api-type web \
  --api-url https://mattieballt-py--sharp-api-fastapi-app.modal.run
```

#### With Custom Focal Length
```bash
python example_client.py \
  --image ~/Desktop/my_photo.jpg \
  --f-px 1500 \
  --api-type web \
  --api-url https://mattieballt-py--sharp-api-fastapi-app.modal.run
```

#### Get JSON Output Instead of PLY
```bash
python example_client.py \
  --image ~/Desktop/my_photo.jpg \
  --format json \
  --api-type web \
  --api-url https://mattieballt-py--sharp-api-fastapi-app.modal.run
```

## Python API Usage

```python
import requests

API_URL = "https://mattieballt-py--sharp-api-fastapi-app.modal.run"

# Upload an image and get Gaussians
with open("my_image.jpg", "rb") as f:
    files = {"file": ("image.jpg", f, "image/jpeg")}
    response = requests.post(f"{API_URL}/predict/ply", files=files)

# Save the PLY file
with open("output.ply", "wb") as f:
    f.write(response.content)
```

## Common Issues

### Issue: `python: command not found`
**Solution**: Use `python3` or activate the venv first with `source venv/bin/activate`

### Issue: `modal deploy` fails with "python-multipart" error
**Solution**: Always run `modal deploy` from within the virtual environment:
```bash
source venv/bin/activate
modal deploy modal_api.py
```

### Issue: pip can't create temp directory
**Solution**: Use the virtual environment instead of system pip:
```bash
source venv/bin/activate
pip install <package>
```

## Viewing Your Deployment

Dashboard: https://modal.com/apps/mattieballt-py/main/deployed/sharp-api

## Redeploying

If you make changes to the code:
```bash
source venv/bin/activate
modal deploy modal_api.py
```
