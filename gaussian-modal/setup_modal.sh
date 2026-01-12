#!/bin/bash
# Quick setup script for Modal deployment

set -e

echo "======================================"
echo "SHARP Modal GPU Setup"
echo "======================================"
echo ""

# Check if modal is installed
if ! command -v modal &> /dev/null
then
    echo "Modal is not installed. Installing..."
    pip install modal
else
    echo "✓ Modal is already installed"
fi

echo ""
echo "======================================"
echo "Setting up Modal account..."
echo "======================================"
echo ""
echo "This will open a browser to authenticate with Modal."
echo "If you already have a Modal account, this will use your existing credentials."
echo ""
read -p "Press Enter to continue..."

modal setup

echo ""
echo "======================================"
echo "Creating Modal token..."
echo "======================================"
echo ""

modal token new

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Deploy the function API:"
echo "   modal deploy modal_app.py"
echo ""
echo "2. OR deploy the web API:"
echo "   modal deploy modal_api.py"
echo ""
echo "3. Test with an image:"
echo "   python example_client.py --image /path/to/image.jpg"
echo ""
echo "For more information, see MODAL_SETUP.md"
echo ""
