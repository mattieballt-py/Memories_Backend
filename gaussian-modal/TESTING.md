# Testing Guide for SHARP Modal Deployment

This guide walks you through testing your Modal deployment step by step.

## Prerequisites

Before testing, ensure you have:

1. Completed Modal setup:
   ```bash
   ./setup_modal.sh
   ```

2. Installed required packages:
   ```bash
   pip install modal requests
   ```

3. A test image ready (JPEG, PNG, HEIC, etc.)

## Step 1: Test Local Modal Setup

Verify Modal is configured correctly:

```bash
modal --version
```

You should see output like: `modal, version 0.63.x`

Check your authentication:

```bash
modal token list
```

You should see your active token.

## Step 2: Deploy the Function API

Deploy the function-based API:

```bash
cd gaussian-modal
modal deploy modal_app.py
```

Expected output:
```
✓ Created objects.
├── 🔨 Created mount /Users/.../gaussian-modal/src/sharp
├── 🔨 Created image (caches warm)
├── 🔨 Created volume sharp-model-cache
└── 🔨 Created function predict and predict_and_save_ply
```

## Step 3: Test Function API with Modal CLI

Test the function directly using Modal's CLI:

```bash
modal run modal_app.py --image-path data/teaser.jpg --output-path test_output.ply
```

Expected behavior:
- First run: Downloads model (~30 seconds)
- Subsequent runs: Uses cached model (~2-5 seconds)
- Creates `test_output.ply` file

Verify the output:
```bash
ls -lh test_output.ply
```

You should see a PLY file (typically 1-5 MB depending on the image).

## Step 4: Test Function API with Python Client

Use the example client:

```bash
python example_client.py \
  --image data/teaser.jpg \
  --output test_output2.ply \
  --api-type function
```

Verify the output:
```bash
ls -lh test_output2.ply
```

## Step 5: Deploy the Web API

Deploy the FastAPI-based web endpoint:

```bash
modal deploy modal_api.py
```

Expected output:
```
✓ Created objects.
...
View Swagger UI at https://your-username--sharp-api-fastapi-app.modal.run/docs
```

**Important**: Copy the URL from the output. You'll use it for testing.

## Step 6: Test Web API Health Check

Test the health endpoint:

```bash
curl https://your-username--sharp-api-fastapi-app.modal.run/health
```

Expected response:
```json
{
  "status": "healthy",
  "cuda_available": true,
  "device": "cuda"
}
```

## Step 7: Test Web API with curl

Test the PLY endpoint:

```bash
curl -X POST "https://your-username--sharp-api-fastapi-app.modal.run/predict/ply" \
  -F "file=@data/teaser.jpg" \
  -o test_web_output.ply
```

Verify the output:
```bash
ls -lh test_web_output.ply
file test_web_output.ply
```

Test the JSON endpoint:

```bash
curl -X POST "https://your-username--sharp-api-fastapi-app.modal.run/predict" \
  -F "file=@data/teaser.jpg" \
  | jq '.metadata'
```

Expected response (partial):
```json
{
  "focal_length": 1920.0,
  "image_size": [1600, 1200],
  "num_gaussians": 50000
}
```

## Step 8: Test Web API with Python Client

Use the example client with the web API:

```bash
python example_client.py \
  --image data/teaser.jpg \
  --output test_web_output2.ply \
  --api-type web \
  --api-url "https://your-username--sharp-api-fastapi-app.modal.run"
```

Test JSON output:

```bash
python example_client.py \
  --image data/teaser.jpg \
  --output test_output.json \
  --api-type web \
  --api-url "https://your-username--sharp-api-fastapi-app.modal.run" \
  --format json
```

## Step 9: Test Batch Processing

Create a test directory with multiple images:

```bash
mkdir -p test_images
cp data/teaser.jpg test_images/image1.jpg
cp data/teaser.jpg test_images/image2.jpg
cp data/teaser.jpg test_images/image3.jpg
```

Run batch processing:

```bash
python example_client.py \
  --image-dir test_images \
  --output-dir test_outputs \
  --api-type function
```

Verify outputs:
```bash
ls -lh test_outputs/
```

You should see PLY files for each input image.

## Step 10: Test with Custom Focal Length

Test with a specific focal length:

```bash
python example_client.py \
  --image data/teaser.jpg \
  --output test_custom_focal.ply \
  --f-px 1500.0 \
  --api-type function
```

## Step 11: Test Web API with Python Requests

Create a test script (`test_api.py`):

```python
import requests
from pathlib import Path

# Replace with your actual URL
API_URL = "https://your-username--sharp-api-fastapi-app.modal.run"

# Test health
response = requests.get(f"{API_URL}/health")
print("Health check:", response.json())

# Test prediction
image_path = "data/teaser.jpg"
with open(image_path, "rb") as f:
    files = {"file": f}
    data = {"f_px": 1200.0}
    response = requests.post(f"{API_URL}/predict/ply", files=files, data=data)

if response.status_code == 200:
    with open("test_api_output.ply", "wb") as f:
        f.write(response.content)
    print("Success! PLY saved to test_api_output.ply")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

Run the test:
```bash
python test_api.py
```

## Step 12: View Logs

Monitor the function API logs:

```bash
modal app logs sharp-view-synthesis
```

Monitor the web API logs:

```bash
modal app logs sharp-api
```

## Step 13: Performance Testing

Test cold start performance:

```bash
# Wait for containers to idle out (5+ minutes)
sleep 360

# Time the request
time python example_client.py \
  --image data/teaser.jpg \
  --output cold_start_test.ply \
  --api-type function
```

Test warm performance:

```bash
# Run immediately after the previous command
time python example_client.py \
  --image data/teaser.jpg \
  --output warm_test.ply \
  --api-type function
```

Compare the times:
- Cold start: ~8-15 seconds
- Warm: ~0.5-2 seconds

## Step 14: Concurrent Request Testing

Test concurrent processing:

```bash
# Create test script (test_concurrent.py)
cat > test_concurrent.py << 'EOF'
import modal
import time
from pathlib import Path

predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")

with open("data/teaser.jpg", "rb") as f:
    image_bytes = f.read()

# Submit 10 concurrent requests
start = time.time()
futures = []
for i in range(10):
    future = predict_fn.spawn(image_bytes)
    futures.append(future)

# Wait for all to complete
results = [f.get() for f in futures]
end = time.time()

print(f"Processed 10 images in {end - start:.2f} seconds")
print(f"Average: {(end - start) / 10:.2f} seconds per image")
EOF

python test_concurrent.py
```

## Step 15: Error Handling Testing

Test with invalid inputs:

```bash
# Test with non-existent file
python example_client.py \
  --image nonexistent.jpg \
  --output error_test.ply \
  --api-type function
```

Expected: Error message about file not found

Test with invalid image:

```bash
# Create invalid file
echo "not an image" > invalid.jpg

python example_client.py \
  --image invalid.jpg \
  --output error_test.ply \
  --api-type function
```

Expected: Error message about image loading

## Troubleshooting

### Problem: "modal: command not found"

Solution:
```bash
pip install modal
```

### Problem: "Authentication failed"

Solution:
```bash
modal setup
modal token new
```

### Problem: "Module 'sharp' not found"

Solution: Ensure you're running from the `gaussian-modal` directory with `src/sharp` present.

### Problem: "CUDA out of memory"

Solution: Edit the Modal files to use a larger GPU:
```python
gpu=modal.gpu.A100(size="80GB")
```

### Problem: "Timeout"

Solution: Increase timeout in the Modal files:
```python
timeout=1200  # 20 minutes
```

### Problem: "Slow first request"

This is expected! The first request:
1. Downloads the model (~2.5GB)
2. Loads it into memory
3. Runs inference

Subsequent requests are much faster.

### Problem: "PLY file is empty or corrupted"

Check:
1. Input image is valid
2. Logs for errors: `modal app logs sharp-view-synthesis`
3. Try with a different image

## Validation

To validate your PLY files, you can:

1. **Check file size**: Should be 1-5 MB typically
   ```bash
   ls -lh output.ply
   ```

2. **Check PLY format**: Should start with "ply"
   ```bash
   head -n 5 output.ply
   ```

3. **View in a 3DGS renderer**: Use any 3D Gaussian Splatting viewer

4. **Check vertex count**:
   ```bash
   grep "element vertex" output.ply
   ```
   Should show tens of thousands of vertices

## Cost Monitoring

Check your Modal dashboard for costs:
- Visit: https://modal.com/dashboard
- View "Usage" tab
- Monitor costs per function

Expected costs:
- Development/testing: <$1/day
- Production (1000 images/day): ~$0.30/day

## Next Steps

After successful testing:

1. **Integrate into your application**
   - Use the Python client code as a reference
   - Implement error handling
   - Add retries for transient failures

2. **Optimize for your use case**
   - Adjust GPU type based on performance needs
   - Configure concurrency based on traffic
   - Set appropriate timeouts

3. **Set up monitoring**
   - Monitor logs regularly
   - Track costs and performance
   - Set up alerts for failures

4. **Production deployment**
   - Use environment variables for configuration
   - Implement rate limiting
   - Add authentication if needed
   - Consider multi-region deployment

## Testing Checklist

- [ ] Modal setup complete
- [ ] Function API deployed
- [ ] Function API tested with Modal CLI
- [ ] Function API tested with Python client
- [ ] Web API deployed
- [ ] Web API health check passes
- [ ] Web API tested with curl
- [ ] Web API tested with Python requests
- [ ] Batch processing tested
- [ ] Custom focal length tested
- [ ] Logs accessible
- [ ] Cold start performance acceptable
- [ ] Warm performance acceptable
- [ ] Concurrent requests working
- [ ] Error handling working
- [ ] PLY files valid
- [ ] Costs within budget

Once all items are checked, you're ready for production use!
