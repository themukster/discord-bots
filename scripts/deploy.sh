#!/bin/bash

# Discord Bots Deployment Script
# This script deploys all Discord bots using PM2

set -e  # Exit on any error

echo "=€ Deploying Discord Bots..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=Á Working directory: $PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "L Virtual environment not found. Please run ./scripts/setup_venv.sh first."
    exit 1
fi

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "=æ Installing PM2..."
    npm install -g pm2
fi

# Check if ecosystem.config.js exists
if [ ! -f "ecosystem.config.js" ]; then
    echo "L ecosystem.config.js not found. Please ensure it exists in the project root."
    exit 1
fi

# Stop any existing PM2 processes for this project
echo "=Ñ Stopping existing processes..."
pm2 delete ecosystem.config.js 2>/dev/null || echo "No existing processes to stop"

# Start all bots using PM2
echo "= Starting bots with PM2..."
pm2 start ecosystem.config.js

# Save PM2 configuration
echo "=¾ Saving PM2 configuration..."
pm2 save

# Setup PM2 startup script (for production servers)
echo "™  Setting up PM2 startup script..."
pm2 startup || echo "PM2 startup setup may require manual configuration"

echo " Deployment complete!"
echo ""
echo "=Ê Bot status:"
pm2 status

echo ""
echo "=' Useful PM2 commands:"
echo "  pm2 status          - Show all processes"
echo "  pm2 logs            - Show logs for all processes"
echo "  pm2 restart all     - Restart all processes"
echo "  pm2 stop all        - Stop all processes"
echo "  pm2 delete all      - Delete all processes"