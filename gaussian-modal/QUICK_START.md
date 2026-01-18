# Quick Start Guide: SHARP Web API

Get your SHARP model HTTP endpoint running in 15 minutes.

## TL;DR

```bash
# 1. Setup Modal
pip install modal boto3
modal setup
modal token new

# 2. Create AWS secret in Modal
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID="your_key" \
  AWS_SECRET_ACCESS_KEY="your_secret" \
  AWS_REGION="us-east-1" \
  S3_BUCKET_NAME="your-bucket-name"

# 3. Deploy
cd gaussian-modal
modal deploy modal_web_api.py

# 4. Test
export API_URL="https://your-username--sharp-web-api-fastapi-app.modal.run"
curl -X POST -F "file=@photo.jpg" $API_URL/splat
```

---

## What You Get

**Input:** User uploads image via HTTP
**Output:** Public S3 URL to PLY file
**Time:** ~2-5 seconds (warm containers)

```
React Frontend
    ↓ POST /splat
Modal GPU (A100)
    ↓ SHARP Model
3D Gaussians
    ↓ Upload
S3 Bucket
    ↓ Presigned URL
React Frontend (displays 3D model)
```

---

## Files Overview

### New Files (Created)

- **`modal_web_api.py`** - Main HTTP endpoint with S3 upload
- **`test_web_api.py`** - Test script for the API
- **`react_example.jsx`** - React component example
- **`WEB_API_SETUP.md`** - Detailed API documentation
- **`DEPLOYMENT_GUIDE.md`** - Complete deployment walkthrough
- **`QUICK_START.md`** - This file

### Existing Files (Unchanged)

- **`modal_app.py`** - Original function-based API (still works)
- **`modal_api.py`** - FastAPI without S3 (still works)
- **`example_client.py`** - Python client (still works)
- **`src/sharp/`** - Model code (unchanged)

---

## Prerequisites

1. **AWS Account** with S3 bucket created
2. **Modal Account** (sign up at https://modal.com)
3. **Python 3.9+** with pip

---

## Setup Steps

### 1. Install Modal

```bash
pip install modal boto3 requests
modal setup  # Opens browser for authentication
modal token new
```

### 2. Create S3 Bucket

```bash
aws s3 mb s3://your-sharp-ply-files --region us-east-1
```

### 3. Store AWS Credentials in Modal

```bash
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID="AKIA..." \
  AWS_SECRET_ACCESS_KEY="..." \
  AWS_REGION="us-east-1" \
  S3_BUCKET_NAME="your-sharp-ply-files"
```

Verify:
```bash
modal secret list
# Should show: aws-credentials
```

### 4. Deploy to Modal

```bash
cd /Users/hedgehog/Desktop/MechEng_Degree/Coding_Things/Memories_Backend/gaussian-modal
modal deploy modal_web_api.py
```

Output will show your API URL:
```
✓ Created web function fastapi_app => https://your-username--sharp-web-api-fastapi-app.modal.run
```

### 5. Test the API

```bash
# Health check
curl https://your-username--sharp-web-api-fastapi-app.modal.run/health

# Upload image
curl -X POST \
  -F "file=@test.jpg" \
  https://your-username--sharp-web-api-fastapi-app.modal.run/splat

# Response:
# {
#   "ply_url": "https://your-bucket.s3.amazonaws.com/...",
#   "metadata": { ... }
# }
```

---

## React Integration

### Option 1: Copy Example Component

```bash
cp react_example.jsx /path/to/your-react-app/src/components/SplatConverter.jsx
```

Then use it:

```jsx
import SplatConverter from './components/SplatConverter';

function App() {
  return (
    <SplatConverter apiUrl="https://your-username--sharp-web-api-fastapi-app.modal.run" />
  );
}
```

### Option 2: DIY Fetch

```jsx
const handleUpload = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('https://your-api.modal.run/splat', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  console.log('PLY URL:', data.ply_url);

  // Load PLY in Three.js or download
};
```

---

## API Reference

### POST /splat

Upload image and get PLY URL.

**Request:**
```bash
curl -X POST \
  -F "file=@photo.jpg" \
  -F "f_px=1200" \
  https://your-api.modal.run/splat
```

**Response:**
```json
{
  "ply_url": "https://bucket.s3.amazonaws.com/ply-files/photo_abc123.ply?AWSAccessKeyId=...",
  "metadata": {
    "original_filename": "photo.jpg",
    "ply_size_bytes": 52428800,
    "focal_length": 1200.0
  }
}
```

**Parameters:**
- `file` (required): Image file (multipart/form-data)
- `f_px` (optional): Focal length in pixels (auto-estimated if omitted)

**Supported formats:** JPEG, PNG, HEIC, WebP

---

## Testing

### Test Script

```bash
python test_web_api.py \
  --api-url https://your-api.modal.run \
  --image test.jpg
```

Output:
```
============================================================
SHARP Web API Test
============================================================
Testing health endpoint: https://your-api.modal.run/health
✓ Health check passed:
  Status: healthy
  CUDA available: True
  Device: cuda
  AWS configured: True

Testing /splat endpoint with image: test.jpg
Uploading image (245678 bytes)...
✓ Success!
  PLY URL: https://bucket.s3.amazonaws.com/...
  Original filename: test.jpg
  PLY size: 50.12 MB
  Focal length: 1404.0

Testing PLY file download...
✓ PLY file downloaded successfully: test_output_test.ply
  Size: 50.12 MB

✓ All tests passed!
```

---

## Common Issues

### "Missing AWS credentials"

```bash
# Check if secret exists
modal secret list

# If missing, create it
modal secret create aws-credentials AWS_ACCESS_KEY_ID="..." ...
```

### "S3 upload failed: Access Denied"

IAM user needs these permissions:
- `s3:PutObject`
- `s3:GetObject`
- `s3:PutObjectAcl`

### CORS errors in browser

Already configured with `allow_origins=["*"]`. For production, restrict to your domain.

### First request is slow

Expected. First request downloads 5GB model (~10-30s). Cached afterwards (~2-5s).

---

## Costs

**Per 1,000 requests:**
- Modal GPU (A100): ~$0.90
- S3 storage (50MB avg): ~$1.15/month
- S3 requests: ~$0.01
- **Total: ~$2-3/month**

(Excludes free tiers)

---

## What's Next?

1. ✅ API deployed and tested
2. ✅ React app can upload images
3. 🎯 Load PLY files in Three.js viewer
4. 🎯 Add authentication if needed
5. 🎯 Monitor costs and optimize
6. 🎯 Deploy React app to production

---

## Full Documentation

- **`WEB_API_SETUP.md`** - API usage and examples
- **`DEPLOYMENT_GUIDE.md`** - Complete deployment walkthrough
- **`modal_web_api.py`** - Source code with comments

---

## Support

**Modal Docs:** https://modal.com/docs
**AWS S3 Docs:** https://docs.aws.amazon.com/s3/
**SHARP Paper:** https://arxiv.org/abs/2512.10685

**Issues:** The existing `modal_app.py` and `modal_api.py` still work. This adds a new web endpoint without breaking anything.

---

## curl Examples

```bash
# Set your API URL
export API_URL="https://your-username--sharp-web-api-fastapi-app.modal.run"

# Health check
curl $API_URL/health

# Info
curl $API_URL/

# Upload image
curl -X POST -F "file=@photo.jpg" $API_URL/splat

# With focal length
curl -X POST -F "file=@photo.jpg" -F "f_px=1200" $API_URL/splat

# Save response
curl -X POST -F "file=@photo.jpg" $API_URL/splat -o response.json

# Extract URL and download PLY
PLY_URL=$(curl -X POST -F "file=@photo.jpg" $API_URL/splat | jq -r '.ply_url')
curl -o output.ply "$PLY_URL"
```

---

## That's It!

You now have a public HTTP endpoint that converts 2D images to 3D Gaussian Splats and returns S3 URLs.

Your React frontend can call this API, get a PLY URL, and load it in Three.js or any other 3D viewer.
