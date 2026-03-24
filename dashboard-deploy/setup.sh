#!/bin/bash
# Quick Start Setup Script for Chakravyuh Dashboard
# This script automates the initial setup process

set -e

echo "🚀 Chakravyuh Dashboard - Quick Setup"
echo "======================================"
echo ""

# Check Node.js installation
echo "✓ Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "✗ Node.js not found. Please install Node.js v18+ from https://nodejs.org"
    exit 1
fi
echo "  Node.js $(node -v)"
echo "  npm $(npm -v)"
echo ""

# Install dependencies
echo "✓ Installing dependencies (this may take a few minutes)..."
npm install --legacy-peer-deps
echo ""

# Create .env file if it doesn't exist
echo "✓ Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env file from .env.example"
    echo "  ⚠️  Update .env with your API URL if needed"
fi
echo ""

# Build the project
echo "✓ Building the dashboard..."
npm run build
echo ""

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update .env with your API endpoint (if not localhost:8000)"
echo "   2. Start development server: npm run dev"
echo "   3. Open http://localhost:5173 in your browser"
echo ""
echo "📚 For more details, read README.md"
