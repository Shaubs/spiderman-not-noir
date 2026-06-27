#!/bin/bash
# Build script for Spider-Man: Not Noir
# Usage: ./build.sh

set -e

echo "🕷️ Building Spider-Man: Not Noir..."
echo "================================================"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Ensure data directory exists
mkdir -p data
if [ ! -f data/scores.json ]; then
    echo '{"scores": []}' > data/scores.json
fi

# Build with PyInstaller
echo "📦 Running PyInstaller..."
pyinstaller spiderman_game.spec --clean

echo ""
echo "================================================"
echo "✅ Build complete!"
echo ""
echo "📁 Output location:"
echo "   - macOS App: dist/SpiderMan-Not-Noir.app"
echo "   - Executable: dist/SpiderMan-Not-Noir/"
echo ""
echo "🚀 To run the app:"
echo "   open dist/SpiderMan-Not-Noir.app"
echo ""
echo "📤 To distribute:"
echo "   1. Zip the .app bundle"
echo "   2. Or create a DMG with create-dmg"
echo "================================================"
