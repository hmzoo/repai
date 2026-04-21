#!/bin/bash
# install.sh - Setup script for RepaI project

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          RepaI - Installation & Setup Script                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python $PYTHON_VERSION"

# Option 1: Create venv
echo ""
echo "📦 Setting up virtual environment..."
python3 -m venv venv
echo "   ✅ Virtual environment created"

# Activate venv
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Source venv/bin/activate in your terminal"

# Install requirements
echo ""
echo "📥 Installing dependencies..."
pip install --quiet -r requirements.txt
echo "   ✅ Dependencies installed"

# Setup .env file
echo ""
echo "🔐 Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✅ .env created from .env.example"
    echo "   ⚠️  Edit .env to add your API keys"
else
    echo "   ℹ️  .env already exists"
fi

# Validate
echo ""
echo "✅ Checking installation..."
python3 validate.py

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  Setup Complete! 🎉                         ║"
echo "║                                                              ║"
echo "║  Next steps:                                                 ║"
echo "║  1. source venv/bin/activate                                │"
echo "║  2. Edit .env with your API keys (if needed)               │"
echo "║  3. python3 example.py                                      │"
echo "║  4. tail -f iteration_log.md                               │"
echo "╚══════════════════════════════════════════════════════════════╝"
