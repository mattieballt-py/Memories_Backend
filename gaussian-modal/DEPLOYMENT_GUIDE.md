# Complete Deployment Guide for SHARP Web API

This guide walks you through deploying the SHARP model as a public HTTP endpoint that your React frontend can call.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS S3 Setup](#aws-s3-setup)
3. [Modal Setup](#modal-setup)
4. [Deployment](#deployment)
5. [Testing](#testing)
6. [React Integration](#react-integration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts

- **AWS Account**: For S3 storage of PLY files
- **Modal Account**: For GPU compute (free tier available)

### Local Setup

```bash
# Install required packages
pip install modal boto3 requests

# Verify installations
modal --version
python -c "import boto3; print('boto3 installed')"
```

---

## AWS S3 Setup

### Step 1: Create S3 Bucket

```bash
# Set variables
export BUCKET_NAME="your-sharp-ply-files"
export AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
```

### Step 2: Configure Bucket CORS (Optional)

If you want to load PLY files directly in the browser:

```bash
cat > cors.json << 'EOF'
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration file://cors.json
```

### Step 3: Create IAM User with S3 Access

```bash
# Create IAM policy
cat > s3-policy.json << EOF
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
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name SharpPlyUploadPolicy \
  --policy-document file://s3-policy.json

# Create IAM user
aws iam create-user --user-name sharp-uploader

# Attach policy to user
aws iam attach-user-policy \
  --user-name sharp-uploader \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/SharpPlyUploadPolicy

# Create access key
aws iam create-access-key --user-name sharp-uploader
```

Save the `AccessKeyId` and `SecretAccessKey` from the output.

### Step 4: Test S3 Access

```bash
# Set credentials
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"

# Test upload
echo "test" > test.txt
aws s3 cp test.txt s3://$BUCKET_NAME/test.txt
aws s3 ls s3://$BUCKET_NAME/
```

---

## Modal Setup

### Step 1: Install and Authenticate Modal

```bash
# Install Modal
pip install modal

# Authenticate (opens browser)
modal setup

# Create token
modal token new
```

### Step 2: Create Modal Secret for AWS Credentials

```bash
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID="your_access_key_here" \
  AWS_SECRET_ACCESS_KEY="your_secret_key_here" \
  AWS_REGION="us-east-1" \
  S3_BUCKET_NAME="your-sharp-ply-files"
```

Verify the secret was created:

```bash
modal secret list
# Should show: aws-credentials
```

### Step 3: Verify Modal Configuration

```bash
# Check your Modal account
modal profile current

# List existing apps
modal app list
```

---

## Deployment

### Step 1: Navigate to Project Directory

```bash
cd /Users/hedgehog/Desktop/MechEng_Degree/Coding_Things/Memories_Backend/gaussian-modal
```

### Step 2: Verify Files

```bash
ls -la
# Should see:
# - modal_web_api.py (new HTTP endpoint)
# - modal_app.py (existing function API)
# - src/sharp/ (model code)
```

### Step 3: Deploy to Modal

```bash
# Deploy the web API
modal deploy modal_web_api.py
```

Expected output:
```
✓ Initialized. View run at https://modal.com/apps/...
✓ Created web function fastapi_app => https://your-username--sharp-web-api-fastapi-app.modal.run

View your app: https://modal.com/apps/...
```

**Save this URL!** This is your API endpoint.

### Step 4: Verify Deployment

```bash
# Set your API URL
export API_URL="https://your-username--sharp-web-api-fastapi-app.modal.run"

# Test health endpoint
curl $API_URL/health

# Expected output:
# {
#   "status": "healthy",
#   "cuda_available": true,
#   "device": "cuda",
#   "aws_configured": true
# }
```

---

## Testing

### Test 1: Health Check

```bash
curl https://your-username--sharp-web-api-fastapi-app.modal.run/health
```

### Test 2: Upload Image (Manual)

```bash
# Download a test image
curl -o test_image.jpg "https://picsum.photos/800/600"

# Upload to API
curl -X POST \
  -F "file=@test_image.jpg" \
  https://your-username--sharp-web-api-fastapi-app.modal.run/splat \
  | jq .

# Expected output:
# {
#   "ply_url": "https://your-bucket.s3.amazonaws.com/ply-files/test_image_a1b2c3d4.ply?...",
#   "metadata": {
#     "original_filename": "test_image.jpg",
#     "ply_size_bytes": 52428800,
#     "focal_length": 960.0
#   }
# }
```

### Test 3: Automated Test Script

```bash
# Use the provided test script
python test_web_api.py \
  --api-url https://your-username--sharp-web-api-fastapi-app.modal.run \
  --image test_image.jpg
```

### Test 4: Download PLY File

```bash
# Extract URL from response
PLY_URL=$(curl -X POST -F "file=@test_image.jpg" $API_URL/splat | jq -r '.ply_url')

# Download PLY file
curl -o output.ply "$PLY_URL"

# Check file size
ls -lh output.ply
# Should be ~50-100 MB
```

---

## React Integration

### Step 1: Install Dependencies

In your React project:

```bash
npm install
# No additional packages needed for basic upload
# Optional: three @react-three/fiber @react-three/drei (for 3D rendering)
```

### Step 2: Copy Example Component

Copy the example React component:

```bash
cp /path/to/gaussian-modal/react_example.jsx \
   /path/to/your-react-app/src/components/SplatConverter.jsx
```

### Step 3: Use in Your App

```jsx
// src/App.jsx
import SplatConverter from './components/SplatConverter';

function App() {
  return (
    <div>
      <SplatConverter
        apiUrl="https://your-username--sharp-web-api-fastapi-app.modal.run"
      />
    </div>
  );
}

export default App;
```

### Step 4: Test in Browser

```bash
npm start
# Open http://localhost:3000
# Upload an image and verify you get a PLY URL back
```

---

## Monitoring & Maintenance

### View Logs

```bash
# View recent logs
modal app logs sharp-web-api

# Stream logs in real-time
modal app logs sharp-web-api --follow

# View logs from last hour
modal app logs sharp-web-api --since 1h
```

### Check Running Containers

```bash
# List all apps
modal app list

# Show app details
modal app show sharp-web-api
```

### Update Deployment

After making code changes:

```bash
# Redeploy
modal deploy modal_web_api.py

# The URL stays the same, changes go live immediately
```

### Cost Monitoring

Visit Modal dashboard: https://modal.com/usage

- View per-request costs
- Monitor GPU usage
- Set spending limits

---

## Troubleshooting

### Issue: "Missing AWS credentials"

**Problem:** Modal can't find AWS secrets.

**Solution:**
```bash
# Verify secret exists
modal secret list

# If missing, create it
modal secret create aws-credentials \
  AWS_ACCESS_KEY_ID="..." \
  AWS_SECRET_ACCESS_KEY="..." \
  AWS_REGION="us-east-1" \
  S3_BUCKET_NAME="your-bucket"

# Redeploy
modal deploy modal_web_api.py
```

### Issue: "S3 upload failed: Access Denied"

**Problem:** IAM permissions are insufficient.

**Solution:**
```bash
# Verify IAM policy
aws iam get-user-policy --user-name sharp-uploader --policy-name SharpPlyUploadPolicy

# Test S3 access manually
aws s3 cp test.txt s3://your-bucket/test.txt --profile sharp-uploader
```

### Issue: "CUDA out of memory"

**Problem:** GPU doesn't have enough VRAM.

**Solution:** Use a larger GPU in `modal_web_api.py`:

```python
@app.function(
    gpu=modal.gpu.A100(size="80GB"),  # Use 80GB instead of 40GB
    ...
)
```

Then redeploy:
```bash
modal deploy modal_web_api.py
```

### Issue: CORS errors in React

**Problem:** Browser blocks cross-origin requests.

**Verify:** CORS is already enabled in the API (`allow_origins=["*"]`).

**For production:** Restrict to your domain:

```python
# In modal_web_api.py
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Your React app domain
    ...
)
```

### Issue: Slow first request

**Expected behavior:** First request downloads the ~5GB model (10-30 seconds).

**Solution:** Subsequent requests use the cached model (~2-5 seconds). This is normal.

To keep containers warm:
```bash
# Ping every 4 minutes
watch -n 240 curl $API_URL/health
```

### Issue: Modal deployment fails

**Check:**
```bash
# Verify Modal authentication
modal token list

# Verify src/sharp directory exists
ls -la src/sharp/

# Try deploying with verbose output
modal deploy modal_web_api.py --show-progress
```

### Issue: PLY URL expires

**Problem:** Presigned URLs expire after 1 hour.

**Options:**
1. Generate new URL by re-uploading
2. Increase expiration time in `modal_web_api.py`:
   ```python
   ExpiresIn=86400  # 24 hours instead of 3600 (1 hour)
   ```
3. Use public S3 URLs (requires bucket policy change)

---

## Production Checklist

Before going to production:

- [ ] Restrict CORS to your domain (not `"*"`)
- [ ] Set up CloudFront CDN in front of S3 for faster downloads
- [ ] Configure S3 lifecycle rules to delete old PLY files
- [ ] Set up Modal alerts for errors/high costs
- [ ] Add rate limiting to prevent abuse
- [ ] Implement authentication if needed
- [ ] Add image size/type validation
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Test with various image formats and sizes
- [ ] Document API for your frontend team

---

## Cost Estimation

### Modal Costs (per request)

- A100 GPU: ~$1.10/hour
- Avg request time: 3 seconds (warm)
- Cost per request: ~$0.0009

### AWS S3 Costs

- Storage: ~$0.023/GB-month
- PUT requests: $0.005 per 1,000
- GET requests: $0.0004 per 1,000
- Data transfer: First 100GB free/month

### Example: 1,000 requests/month

- Modal: 1,000 × $0.0009 = $0.90
- S3 storage (50MB × 1,000): ~$1.15
- S3 requests: ~$0.01
- **Total: ~$2/month** (excluding free tiers)

---

## Next Steps

1. ✅ AWS S3 bucket created and configured
2. ✅ Modal account set up with secrets
3. ✅ API deployed to Modal
4. ✅ API tested with curl and test script
5. ✅ React component integrated
6. 🎯 Deploy React app to production
7. 🎯 Monitor costs and usage
8. 🎯 Optimize based on user feedback

---

## Support & Resources

- **Modal Docs**: https://modal.com/docs
- **AWS S3 Docs**: https://docs.aws.amazon.com/s3/
- **SHARP Paper**: https://arxiv.org/abs/2512.10685
- **Project Issues**: Create issues on your repo

---

## Alternative: Modal Volume Storage

If you don't want to use S3, you can serve files from Modal volumes:

```python
# Create volume for PLY files
ply_storage = modal.Volume.from_name("ply-files", create_if_missing=True)

# Serve files via Modal
@app.function(
    volumes={"/ply-files": ply_storage},
)
@modal.web_endpoint(method="GET")
def serve_ply(filename: str):
    from fastapi.responses import FileResponse
    return FileResponse(f"/ply-files/{filename}")
```

However, S3 is recommended for:
- Better download performance
- Built-in CDN capabilities
- No Modal compute costs for file serving
- More reliable public URLs
