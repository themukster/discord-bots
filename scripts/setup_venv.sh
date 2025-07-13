#!/bin/bash

# Discord Bots Virtual Environment Setup Script
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on any error

echo "=€ Setting up Discord Bots environment..."

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "L Python3 is not installed. Please install Python 3.8+ before running this script."
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=Á Working directory: $PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "=' Creating Python virtual environment..."
    python3 -m venv venv
else
    echo " Virtual environment already exists"
fi

# Activate virtual environment
echo "= Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "=æ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "=Ú Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo " Environment setup complete!"
echo ""
echo "<¯ Next steps:"
echo "1. Copy .env.example files to .env in each bot directory"
echo "2. Fill in your Discord tokens and API keys"
echo "3. Run ./scripts/deploy.sh to start the bots"
echo ""
echo "To activate the environment manually:"
echo "source venv/bin/activate"