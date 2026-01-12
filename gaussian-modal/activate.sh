#!/bin/bash
# Quick activation script for the gaussian-modal venv
# Usage: source activate.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"

echo "✓ Virtual environment activated"
echo ""
echo "Quick commands:"
echo "  python quick_test.py <image.jpg>    # Test the API"
echo "  python example_client.py --help      # See all options"
echo "  modal deploy modal_api.py            # Redeploy changes"
echo ""
echo "Your API: https://mattieballt-py--sharp-api-fastapi-app.modal.run"
