#!/usr/bin/env bash
# Render build script for Playwright

set -o errexit  # Exit on error

echo "============================================"
echo "Installing Python dependencies..."
echo "============================================"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "============================================"
echo "Installing Playwright browsers..."
echo "============================================"
playwright install chromium

echo ""
echo "============================================"
echo "Installing system dependencies for Playwright..."
echo "============================================"
playwright install-deps chromium

echo ""
echo "============================================"
echo "Build completed successfully!"
echo "============================================"
