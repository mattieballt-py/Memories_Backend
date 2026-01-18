# SHARP Web API Setup Guide

This guide explains how to deploy and use the SHARP model as an HTTP endpoint that uploads PLY files to S3.

## Architecture

```
React Frontend → HTTP POST /splat → Modal GPU Container → SHARP Model → S3 Upload → Return URL
```

## Prerequisites

### 1. AWS Setup

Create an S3 bucket for storing PLY files:

```bash
# Create S3 bucket (choose a unique name)
aws s3 mb s3://your-ply-files-bucket

# Optional: Configure CORS if you want direct browser access
aws s3api put-bucket-cors --bucket your-ply-files-bucket --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}'
```

### 2. Modal Setup

Install Modal CLI:
```bash
pip install modal
```

Authenticate with Modal:
```bash
modal setup
```

### 3. Store AWS Credentials in Modal

Modal uses "secrets" to securely store credentials. Create a secret named `aws-credentials`:

```bash
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID=your_access_key \
  AWS_SECRET_ACCESS_KEY=your_secret_key \
  AWS_REGION=us-east-1 \
  S3_BUCKET_NAME=your-ply-files-bucket
```

Alternatively, you can create secrets via the Modal web dashboard at https://modal.com/secrets

## Deployment

### Deploy the Web API

```bash
cd /Users/hedgehog/Desktop/MechEng_Degree/Coding_Things/Memories_Backend/gaussian-modal
modal deploy modal_web_api.py
```

This will output a URL like:
```
✓ Created web function fastapi_app => https://your-username--sharp-web-api-fastapi-app.modal.run
```

Save this URL - your React frontend will use it!

## API Endpoints

### `POST /splat`

Upload an image and get back a public URL to the generated PLY file.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Fields:
  - `file` (required): Image file (JPEG, PNG, HEIC, WebP)
  - `f_px` (optional): Focal length in pixels (auto-estimated if not provided)

**Response:**
```json
{
  "ply_url": "https://your-bucket.s3.amazonaws.com/ply-files/photo_a1b2c3d4.ply?...",
  "metadata": {
    "original_filename": "photo.jpg",
    "ply_size_bytes": 52428800,
    "focal_length": 1404.0
  }
}
```

**Error Responses:**
- `400`: Invalid file type or empty file
- `500`: Model inference error or S3 upload error

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "cuda_available": true,
  "device": "cuda",
  "aws_configured": true
}
```

### `GET /`

API information endpoint.

## Usage Examples

### Using curl

```bash
# Basic usage
curl -X POST \
  -F "file=@/path/to/photo.jpg" \
  https://your-username--sharp-web-api-fastapi-app.modal.run/splat

# With custom focal length
curl -X POST \
  -F "file=@photo.jpg" \
  -F "f_px=1200" \
  https://your-username--sharp-web-api-fastapi-app.modal.run/splat

# Save response to file
curl -X POST \
  -F "file=@photo.jpg" \
  https://your-username--sharp-web-api-fastapi-app.modal.run/splat \
  -o response.json

# Health check
curl https://your-username--sharp-web-api-fastapi-app.modal.run/health
```

### Using Python

```python
import requests

API_URL = "https://your-username--sharp-web-api-fastapi-app.modal.run"

# Upload image
with open("photo.jpg", "rb") as f:
    files = {"file": ("photo.jpg", f, "image/jpeg")}
    response = requests.post(f"{API_URL}/splat", files=files)

if response.ok:
    data = response.json()
    ply_url = data["ply_url"]
    print(f"PLY file available at: {ply_url}")

    # Download the PLY file
    ply_response = requests.get(ply_url)
    with open("output.ply", "wb") as f:
        f.write(ply_response.content)
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### React Frontend Integration

```jsx
import { useState } from 'react';

function SplatConverter() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [plyUrl, setPlyUrl] = useState(null);

  const API_URL = "https://your-username--sharp-web-api-fastapi-app.modal.run";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setPlyUrl(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/splat`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error);
      }

      const data = await response.json();
      setPlyUrl(data.ply_url);

      console.log('PLY URL:', data.ply_url);
      console.log('Metadata:', data.metadata);

      // Now you can load this URL in Three.js or other 3D viewer
      // Example: loadPLY(data.ply_url);

    } catch (error) {
      console.error('Error:', error);
      alert('Failed to generate 3D model: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>2D Photo → 3D Model</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files[0])}
          disabled={loading}
        />
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Generating 3D Model...' : 'Upload & Convert'}
        </button>
      </form>

      {plyUrl && (
        <div>
          <p>✅ 3D model ready!</p>
          <a href={plyUrl} download>Download PLY</a>
          {/* Load PLY in Three.js viewer here */}
        </div>
      )}
    </div>
  );
}

export default SplatConverter;
```

## Testing Locally

You can test the endpoint locally before deploying:

```bash
# Run locally (this will spin up a temporary Modal container)
modal serve modal_web_api.py
```

This will give you a temporary URL like `https://your-username--sharp-web-api-fastapi-app-dev.modal.run` for testing.

## Performance & Costs

**Cold Start:**
- First request: ~10-30 seconds (downloading model checkpoint)
- Subsequent requests: ~2-5 seconds (model cached)

**Processing Time:**
- Model inference: ~0.5-1 second on A100
- S3 upload: ~0.5-2 seconds (depends on PLY size, typically 50-100MB)
- Total: ~3-7 seconds for warm containers

**Modal Costs (approximate):**
- A100 GPU: ~$1.10/hour compute time
- Storage (model cache): ~$0.15/GB-month
- Cost per request: ~$0.001-0.002 (warm container)

**AWS S3 Costs:**
- Storage: ~$0.023/GB-month (Standard)
- PUT requests: $0.005 per 1,000 requests
- GET requests (presigned URLs): $0.0004 per 1,000 requests
- Data transfer out: First 100GB free/month, then $0.09/GB

## Container Management

**Auto-scaling:**
- Containers scale from 0 to N based on demand
- Up to 10 concurrent requests per container
- Containers idle timeout after 5 minutes (configurable)

**Keep containers warm:**
To reduce cold starts, you can ping the `/health` endpoint periodically:

```bash
# Every 4 minutes to prevent idle timeout
watch -n 240 curl https://your-username--sharp-web-api-fastapi-app.modal.run/health
```

## Monitoring & Debugging

**View logs:**
```bash
modal app logs sharp-web-api
```

**List deployed apps:**
```bash
modal app list
```

**View recent requests:**
```bash
modal app logs sharp-web-api --since 1h
```

## Troubleshooting

### Error: "Missing AWS credentials"

Make sure you've created the Modal secret:
```bash
modal secret list
# Should show 'aws-credentials'
```

If not, create it:
```bash
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID=xxx \
  AWS_SECRET_ACCESS_KEY=xxx \
  AWS_REGION=us-east-1 \
  S3_BUCKET_NAME=your-bucket
```

### Error: "S3 upload failed: Access Denied"

Check your AWS IAM permissions. The credentials need:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

### CORS errors from React

If you get CORS errors, the API already has CORS enabled (`allow_origins=["*"]`). For production, change this to your specific domain:

```python
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-react-app.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then redeploy:
```bash
modal deploy modal_web_api.py
```

### Slow first request

The first request downloads the ~5GB model checkpoint. Subsequent requests use the cached model. This is expected behavior.

## Alternative: Modal Volume with Web Server

If you prefer NOT to use S3, you can serve PLY files directly from Modal using a web server and volume:

```python
# Create a volume for storing PLY files
ply_storage = modal.Volume.from_name("ply-files", create_if_missing=True)

# Mount it in your function
@app.function(
    volumes={"/ply-files": ply_storage},
    ...
)

# Save PLY to volume
ply_path = f"/ply-files/{unique_id}.ply"
with open(ply_path, "wb") as f:
    f.write(ply_bytes)
ply_storage.commit()

# Return Modal volume URL
return {"ply_url": f"https://your-app.modal.run/files/{unique_id}.ply"}
```

Then add a file serving endpoint. However, S3 is recommended for production as it provides:
- Better download speeds
- No Modal container needed for file serving
- Built-in CDN capabilities
- More reliable for public URLs

## Next Steps

1. Deploy the API: `modal deploy modal_web_api.py`
2. Test with curl using a sample image
3. Integrate the API URL into your React frontend
4. Load the returned PLY URL in Three.js or your 3D viewer

## Existing API Unchanged

The original function-based API in `modal_app.py` remains fully functional:

```python
import modal

predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

with open("image.jpg", "rb") as f:
    ply_bytes = predict_fn.remote(f.read())
```

Both APIs can coexist and be used for different purposes:
- `modal_web_api.py`: HTTP endpoint for React frontend
- `modal_app.py`: Direct function calls for Python batch processing
