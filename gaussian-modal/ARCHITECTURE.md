# SHARP Modal Architecture

## Overview

This document describes the architecture of the SHARP model deployment on Modal GPUs.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  • Python Client (example_client.py)                            │
│  • HTTP/REST Client (curl, requests, etc.)                      │
│  • Your Application                                             │
└────────────┬────────────────────────────────┬───────────────────┘
             │                                │
             │                                │
             ▼                                ▼
┌─────────────────────────┐    ┌─────────────────────────────────┐
│   Function API          │    │      Web API                    │
│   (modal_app.py)        │    │   (modal_api.py)                │
├─────────────────────────┤    ├─────────────────────────────────┤
│ • predict()             │    │ • GET /                         │
│ • predict_and_save_ply()│    │ • GET /health                   │
│                         │    │ • POST /predict                 │
│                         │    │ • POST /predict/ply             │
└────────────┬────────────┘    └────────────┬────────────────────┘
             │                              │
             └──────────────┬───────────────┘
                            │
                            ▼
             ┌──────────────────────────────┐
             │      Modal Infrastructure    │
             ├──────────────────────────────┤
             │  • GPU Allocation (A100/H100)│
             │  • Container Management      │
             │  • Auto-scaling              │
             │  • Request Queuing           │
             └──────────────┬───────────────┘
                            │
                            ▼
             ┌──────────────────────────────┐
             │     Model Execution          │
             ├──────────────────────────────┤
             │  1. Load Image               │
             │  2. Preprocess               │
             │  3. Run SHARP Model          │
             │  4. Post-process Gaussians   │
             │  5. Return Results           │
             └──────────────┬───────────────┘
                            │
                            ▼
             ┌──────────────────────────────┐
             │    Model Cache Volume        │
             ├──────────────────────────────┤
             │  • Model Checkpoint (2.5GB)  │
             │  • Persistent across runs    │
             └──────────────────────────────┘
```

## Components

### 1. Client Layer

**Python Client (`example_client.py`)**
- Command-line interface for single/batch processing
- Supports both function and web API
- Handles file I/O and result saving

**HTTP Clients**
- Any HTTP client (curl, requests, etc.)
- Direct REST API access
- JSON or binary PLY responses

**Your Application**
- Integrate via Python SDK or HTTP requests
- Asynchronous processing supported
- Batch processing capabilities

### 2. Modal Functions

**Function API (`modal_app.py`)**
- Direct function calls via Modal SDK
- Two functions:
  - `predict()`: Returns JSON with Gaussian parameters
  - `predict_and_save_ply()`: Returns PLY file bytes
- Lower latency for programmatic access
- Ideal for Python applications

**Web API (`modal_api.py`)**
- FastAPI-based REST endpoints
- Four endpoints:
  - `GET /`: API information
  - `GET /health`: Health check
  - `POST /predict`: JSON response
  - `POST /predict/ply`: Binary PLY response
- Standard HTTP interface
- Language-agnostic

### 3. Modal Infrastructure

**GPU Allocation**
- Configurable GPU types (T4, A10G, A100, H100)
- Default: A100 40GB
- Automatic provisioning and deallocation

**Container Management**
- Cold start: ~5-10 seconds
- Warm containers: <1 second overhead
- Configurable idle timeout (default: 5 minutes)

**Auto-scaling**
- Scales from 0 to N containers
- Concurrent request handling (default: 10)
- Cost-effective: pay only for compute time

**Request Queuing**
- Automatic queue management
- Fair request distribution
- Handles burst traffic

### 4. Model Execution Pipeline

**Stage 1: Load Image**
- Support multiple formats (JPEG, PNG, HEIC, etc.)
- RGB conversion
- Dimension extraction

**Stage 2: Preprocess**
- Resize to 1536x1536 (internal resolution)
- Normalize to [0, 1]
- Estimate focal length if not provided

**Stage 3: Run SHARP Model**
- Single feedforward pass
- Predicts 3D Gaussian parameters in NDC space
- ~500ms on A100 GPU

**Stage 4: Post-process**
- Convert NDC to metric space
- Apply camera intrinsics
- Unproject Gaussians

**Stage 5: Return Results**
- JSON format: All parameters as arrays
- PLY format: Standard 3DGS file

### 5. Model Cache

**Volume Storage**
- Persistent Modal Volume
- Shared across all containers
- Automatic checkpoint management

**Caching Strategy**
- Download on first access
- Persist in volume
- Reuse across invocations
- ~2.5GB storage

## Data Flow

### Single Image Processing

```
Image File → Client → Modal Function → GPU Container
                                            ↓
                                    Load from Cache
                                            ↓
                                    SHARP Inference
                                            ↓
                                    Gaussian Output
                                            ↓
Client ← JSON/PLY ← Modal Function ← GPU Container
```

### Batch Processing

```
Image Dir → Client
              ↓
         Parallel Submit
              ↓
    ┌─────┬──┴───┬─────┐
    ↓     ↓      ↓     ↓
  GPU1  GPU2  GPU3  GPU4  (Auto-scaled)
    ↓     ↓      ↓     ↓
    └─────┴──┬───┴─────┘
             ↓
        Collect Results
             ↓
         Output Dir
```

## Performance Characteristics

### Latency Breakdown

**Cold Start** (first request or after idle timeout):
- Container initialization: 5-10 seconds
- Model download (first ever): 20-30 seconds
- Model load from cache: 2-3 seconds
- Inference: 0.5-1 seconds
- **Total: ~8-15 seconds** (or ~30-40s on very first run)

**Warm Container** (subsequent requests):
- Queue time: <100ms
- Model inference: 0.5-1 seconds
- **Total: ~0.5-1.5 seconds**

### Throughput

**Single GPU (A100)**:
- ~1 image per second (warm)
- ~10 concurrent requests supported

**Auto-scaled** (unlimited GPUs):
- ~10N images per second (N = number of GPUs)
- Scales automatically based on load

### Cost Analysis

**Per-Image Cost** (A100 40GB at $1.10/hour):
- Cold start: ~$0.005
- Warm inference: ~$0.0003
- Network egress: ~$0.0001 (1MB PLY)

**Monthly Cost Examples**:
- 1,000 images/month: ~$0.50
- 10,000 images/month: ~$4.00
- 100,000 images/month: ~$35.00

## Configuration Options

### GPU Selection

```python
# Budget option - Good for development
gpu=modal.gpu.T4()  # ~$0.20/hour

# Balanced option
gpu=modal.gpu.A10G()  # ~$0.60/hour

# High performance (default)
gpu=modal.gpu.A100(size="40GB")  # ~$1.10/hour

# Maximum performance
gpu=modal.gpu.H100()  # ~$2.50/hour
```

### Concurrency

```python
# Low concurrency - Cheaper but slower
allow_concurrent_inputs=1

# Default
allow_concurrent_inputs=10

# High concurrency - Faster but more expensive
allow_concurrent_inputs=20
```

### Container Lifetime

```python
# Short timeout - Lower costs, more cold starts
container_idle_timeout=60  # 1 minute

# Default
container_idle_timeout=300  # 5 minutes

# Long timeout - Fewer cold starts, higher costs
container_idle_timeout=900  # 15 minutes
```

### Timeout

```python
# Quick timeout for fast failures
timeout=300  # 5 minutes

# Default
timeout=600  # 10 minutes

# Long timeout for complex processing
timeout=1800  # 30 minutes
```

## Error Handling

### Common Errors

1. **CUDA Out of Memory**
   - Solution: Use larger GPU (A100 80GB or H100)

2. **Timeout**
   - Solution: Increase timeout or use faster GPU

3. **Module Not Found**
   - Solution: Verify `src/sharp` directory is copied correctly

4. **Authentication Error**
   - Solution: Run `modal setup` and `modal token new`

### Retry Strategy

Modal automatically retries failed requests:
- Network errors: 3 retries
- Container crashes: 2 retries
- Timeout: 1 retry

## Security Considerations

1. **Authentication**: Modal tokens are user-specific
2. **Isolation**: Each container is isolated
3. **Input Validation**: Client should validate inputs
4. **Rate Limiting**: Consider implementing in production

## Monitoring

### Logs

```bash
# View real-time logs
modal app logs sharp-view-synthesis

# View web API logs
modal app logs sharp-api
```

### Metrics

- Request count
- Average latency
- GPU utilization
- Error rate
- Cost per request

Access via Modal dashboard: https://modal.com/dashboard

## Deployment Strategies

### Development
- Use smaller GPU (T4 or A10G)
- Short container timeout
- Low concurrency

### Staging
- Use A100 GPU
- Medium container timeout (5 min)
- Medium concurrency (10)

### Production
- Use A100 or H100 GPU
- Longer container timeout (10-15 min)
- Higher concurrency (20+)
- Set up monitoring and alerts
- Implement rate limiting
- Consider multiple regions

## Extending the System

### Custom Preprocessing

Add custom preprocessing in the image loading step:

```python
def custom_preprocess(image_bytes):
    # Your preprocessing logic
    return processed_image
```

### Custom Post-processing

Add custom post-processing after Gaussian generation:

```python
def custom_postprocess(gaussians):
    # Your post-processing logic
    return modified_gaussians
```

### Additional Endpoints

Add new endpoints to the FastAPI app:

```python
@web_app.post("/predict/custom")
async def custom_endpoint(...):
    # Your custom logic
    pass
```

### Multiple Models

Support multiple model versions:

```python
@app.function(...)
def predict_v2(image_bytes, model_version="v2"):
    checkpoint_path = f"{MODEL_CACHE_PATH}/sharp_{model_version}.pt"
    # Load and run appropriate model
```

## Best Practices

1. **Use appropriate GPU for your workload**
   - Development: T4 or A10G
   - Production: A100 or H100

2. **Implement caching at the client level**
   - Cache results for identical inputs
   - Reduces API calls and costs

3. **Batch process when possible**
   - Submit multiple images in parallel
   - Better GPU utilization

4. **Monitor and optimize**
   - Track latency and costs
   - Adjust configuration based on usage patterns

5. **Handle errors gracefully**
   - Implement retry logic
   - Log failures for debugging

6. **Secure your deployment**
   - Validate inputs
   - Implement rate limiting
   - Monitor for abuse

## Future Enhancements

Potential improvements to consider:

1. **Video Processing**: Support video input for multi-frame Gaussians
2. **Batch API**: Dedicated endpoint for batch processing
3. **Webhooks**: Async processing with callbacks
4. **Model Fine-tuning**: Support custom model checkpoints
5. **Region Selection**: Deploy to multiple regions for lower latency
6. **Cost Optimization**: Automatic GPU selection based on load
