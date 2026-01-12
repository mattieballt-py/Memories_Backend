# Memories Backend

Backend server for the Memories application.

## Project Structure

### gaussian-modal/
SHARP view synthesis model deployment on Modal GPUs. This directory contains:
- SHARP model for generating 3D Gaussian representations from single images
- Modal deployment configurations for serverless GPU inference
- REST API endpoints for easy integration

See [gaussian-modal/README.md](gaussian-modal/README.md) and [gaussian-modal/MODAL_SETUP.md](gaussian-modal/MODAL_SETUP.md) for detailed setup instructions.

## Quick Start - Modal GPU Deployment

```bash
# Navigate to the gaussian-modal directory
cd gaussian-modal

# Run the setup script
./setup_modal.sh

# Deploy the API
modal deploy modal_api.py

# Test with an image
python example_client.py --image /path/to/image.jpg --output output.ply
```

## Getting Started

This project is under development.
