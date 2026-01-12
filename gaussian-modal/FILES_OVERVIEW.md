# Files Overview

This document provides an overview of all the Modal deployment files in this directory.

## Core Files

### `modal_app.py`
**Purpose**: Function-based Modal deployment

**What it does**:
- Provides direct Modal function calls for inference
- Two functions: `predict()` (JSON) and `predict_and_save_ply()` (PLY)
- Includes local entrypoint for CLI testing
- Best for: Python applications using Modal SDK

**Usage**:
```bash
# Deploy
modal deploy modal_app.py

# Test locally
modal run modal_app.py --image-path image.jpg --output-path output.ply

# Use in Python
import modal
predict_fn = modal.Function.lookup("sharp-view-synthesis", "predict_and_save_ply")
ply_bytes = predict_fn.remote(image_bytes)
```

---

### `modal_api.py`
**Purpose**: FastAPI web endpoint deployment

**What it does**:
- Provides REST API with HTTP endpoints
- Four endpoints: `/`, `/health`, `/predict`, `/predict/ply`
- Standard web interface for any HTTP client
- Best for: Web applications, cross-language integration

**Usage**:
```bash
# Deploy
modal deploy modal_api.py

# Test with curl
curl -X POST "https://your-url/predict/ply" \
  -F "file=@image.jpg" \
  -o output.ply
```

---

### `example_client.py`
**Purpose**: Example client for both APIs

**What it does**:
- Command-line client for testing deployments
- Supports single image and batch processing
- Works with both function and web APIs
- Demonstrates how to integrate into your code

**Usage**:
```bash
# Function API
python example_client.py --image img.jpg --api-type function

# Web API
python example_client.py --image img.jpg --api-type web --api-url "https://your-url"

# Batch processing
python example_client.py --image-dir images/ --output-dir outputs/
```

---

## Setup and Configuration

### `setup_modal.sh`
**Purpose**: Automated setup script

**What it does**:
- Installs Modal if needed
- Runs Modal authentication setup
- Creates Modal token
- Provides next steps

**Usage**:
```bash
./setup_modal.sh
```

---

### `requirements-modal.txt`
**Purpose**: Python dependencies for Modal deployment

**What it does**:
- Lists required packages (modal, requests)
- Only for local machine, not Modal containers
- Modal containers get dependencies via image definition

**Usage**:
```bash
pip install -r requirements-modal.txt
```

---

## Documentation

### `MODAL_SETUP.md`
**Purpose**: Complete setup and deployment guide

**Contents**:
- Prerequisites and installation
- Deployment instructions for both APIs
- Configuration options (GPU, concurrency, timeouts)
- Cost analysis and optimization
- Troubleshooting guide
- Advanced usage examples

**When to read**: Before deploying for the first time

---

### `ARCHITECTURE.md`
**Purpose**: System architecture documentation

**Contents**:
- System architecture diagrams
- Component descriptions
- Data flow visualization
- Performance characteristics
- Cost breakdown
- Configuration options explained
- Best practices
- Future enhancements

**When to read**: To understand how everything works together

---

### `TESTING.md`
**Purpose**: Step-by-step testing guide

**Contents**:
- 15-step testing procedure
- Commands for each test
- Expected outputs
- Troubleshooting common issues
- Performance testing
- Validation procedures
- Testing checklist

**When to read**: After deployment to verify everything works

---

### `FILES_OVERVIEW.md` (this file)
**Purpose**: Quick reference for all files

**When to read**: To understand what each file does

---

## Original Project Files

### `src/sharp/`
**Purpose**: SHARP model source code

**Contents**:
- Model implementations
- CLI tools
- Utilities for image processing and Gaussian handling
- Original Apple ML-SHARP code

**Note**: This is copied into Modal containers during deployment

---

### `requirements.txt`
**Purpose**: Dependencies for local SHARP installation

**Usage**:
```bash
pip install -r requirements.txt
```

---

### `pyproject.toml`
**Purpose**: Python project configuration

**Contents**:
- Project metadata
- Dependencies
- CLI entry points
- Build system configuration

---

## Workflow Guide

### First-Time Setup
1. Read [`MODAL_SETUP.md`](MODAL_SETUP.md) - Prerequisites section
2. Run [`setup_modal.sh`](setup_modal.sh) - Authentication
3. Read [`MODAL_SETUP.md`](MODAL_SETUP.md) - Deployment section

### Deployment
1. Choose API type (function vs web)
2. Deploy using `modal deploy modal_app.py` or `modal deploy modal_api.py`
3. Note the URL (for web API)

### Testing
1. Follow [`TESTING.md`](TESTING.md) step by step
2. Use [`example_client.py`](example_client.py) for testing
3. Check logs with `modal app logs`

### Integration
1. Review [`example_client.py`](example_client.py) code
2. Copy relevant code into your application
3. Add error handling and retries
4. Test with your data

### Optimization
1. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) - Configuration section
2. Adjust GPU type, concurrency, timeouts
3. Monitor costs in Modal dashboard
4. Iterate based on usage patterns

## Quick Command Reference

```bash
# Setup
./setup_modal.sh

# Deploy
modal deploy modal_app.py          # Function API
modal deploy modal_api.py          # Web API

# Test
modal run modal_app.py --image-path img.jpg --output-path out.ply
python example_client.py --image img.jpg --api-type function

# Monitor
modal app logs sharp-view-synthesis  # Function API logs
modal app logs sharp-api             # Web API logs
modal app list                       # List deployed apps

# Manage
modal app stop sharp-view-synthesis  # Stop function API
modal app stop sharp-api             # Stop web API
```

## File Dependencies

```
modal_app.py
├── src/sharp/              (copied into container)
└── sharp-model-cache       (Modal volume)

modal_api.py
├── src/sharp/              (copied into container)
└── sharp-model-cache       (Modal volume)

example_client.py
├── modal_app.py            (if using function API)
└── modal_api.py            (if using web API)

setup_modal.sh
└── (no dependencies)
```

## Choosing Which API to Use

### Use Function API (`modal_app.py`) when:
- You're building a Python application
- You want lower latency
- You prefer programmatic SDK access
- You need direct function calls

### Use Web API (`modal_api.py`) when:
- You need HTTP/REST endpoints
- You're integrating from non-Python languages
- You want a standard web interface
- You need easy testing with curl/Postman

### Use Both when:
- You have multiple client types
- You want maximum flexibility
- Cost is not a primary concern (both APIs run independently)

## Next Steps

1. **New to Modal?** 
   → Start with [`MODAL_SETUP.md`](MODAL_SETUP.md)

2. **Ready to deploy?**
   → Run [`setup_modal.sh`](setup_modal.sh), then deploy

3. **Want to understand the system?**
   → Read [`ARCHITECTURE.md`](ARCHITECTURE.md)

4. **Need to test?**
   → Follow [`TESTING.md`](TESTING.md)

5. **Ready to integrate?**
   → Copy code from [`example_client.py`](example_client.py)

6. **Having issues?**
   → Check troubleshooting sections in the guides

## Support

- **Modal Docs**: https://modal.com/docs
- **SHARP Paper**: https://arxiv.org/abs/2512.10685
- **SHARP Project**: https://apple.github.io/ml-sharp/
- **Modal Discord**: https://discord.gg/modal

## License

This Modal deployment code follows the same license as the original SHARP project.
See [`LICENSE`](LICENSE) and [`LICENSE_MODEL`](LICENSE_MODEL) for details.
