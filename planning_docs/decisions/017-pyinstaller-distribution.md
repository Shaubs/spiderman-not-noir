# ADR-017: PyInstaller Distribution Packaging

## Status
**Accepted** - June 26, 2026

## Context

We need to distribute the Spider-Man: Not Noir game to end users who may not have Python installed. The game has several dependencies including:
- OpenCV (cv2)
- MediaPipe
- PyTorch
- NumPy
- PIL

We need a solution that:
1. Creates a standalone executable
2. Bundles all Python dependencies
3. Works on macOS (primary target)
4. Includes all game assets (THWIP images, ML models, task files)

## Decision

We chose **PyInstaller** for packaging the game into a distributable macOS application.

### Why PyInstaller?

1. **Mature and well-supported** - Most popular Python packaging tool
2. **Good macOS support** - Creates proper .app bundles with Info.plist
3. **Handles complex dependencies** - Built-in hooks for torch, cv2, mediapipe
4. **Single command build** - Can be automated in CI/CD

### Alternatives Considered

| Tool | Pros | Cons |
|------|------|------|
| **cx_Freeze** | Lightweight | Poor macOS app bundle support |
| **py2app** | Native macOS | Limited to macOS only, less active |
| **Nuitka** | Compiles to C, fast | Complex setup, long build times |
| **Docker** | Consistent environment | Overkill for a game, bad UX |

## Implementation

### Installation

```bash
pip install pyinstaller
```

### Build Command

```bash
pyinstaller --onedir --windowed --name "SpiderMan-Not-Noir" \
  --add-data "assets/thwip.png:assets" \
  --add-data "ffnn_classifier/model.pt:ffnn_classifier" \
  --add-data "hand_landmarker.task:." \
  --add-data "pose_landmarker.task:." \
  --add-data "data:data" \
  --hidden-import mediapipe \
  --hidden-import cv2 \
  --hidden-import torch \
  --collect-data mediapipe \
  game.py
```

### Build Options Explained

| Option | Purpose |
|--------|---------|
| `--onedir` | Creates a directory with executable + dependencies (vs single file) |
| `--windowed` | No console window (GUI app) |
| `--name` | Output app name |
| `--add-data "src:dest"` | Bundle data files (colon separates source:destination) |
| `--hidden-import` | Force include modules not detected by analysis |
| `--collect-data` | Include package's data files (required for mediapipe) |

### Output Structure

```
dist/
├── SpiderMan-Not-Noir/          # Folder distribution
│   ├── SpiderMan-Not-Noir       # Main executable
│   ├── assets/
│   ├── ffnn_classifier/
│   ├── data/
│   └── ... (bundled libraries)
│
└── SpiderMan-Not-Noir.app/      # macOS app bundle
    └── Contents/
        ├── Info.plist           # App metadata
        ├── MacOS/               # Executable
        ├── Frameworks/          # Bundled libraries (~200MB)
        └── Resources/           # App resources
```

### Build Size

The final `.app` bundle is approximately **205MB**, primarily due to:
- PyTorch: ~150MB
- MediaPipe: ~30MB
- OpenCV: ~20MB
- Other dependencies: ~5MB

## Distribution Methods

### Option 1: Zip the App Bundle

```bash
cd dist
zip -r SpiderMan-Not-Noir-macOS-arm64.zip SpiderMan-Not-Noir.app
```

Users can download, unzip, and double-click to run.

### Option 2: Create DMG (Disk Image)

```bash
# Install create-dmg
brew install create-dmg

# Create DMG
create-dmg \
  --volname "Spider-Man: Not Noir" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "SpiderMan-Not-Noir.app" 200 190 \
  --hide-extension "SpiderMan-Not-Noir.app" \
  --app-drop-link 600 185 \
  "SpiderMan-Not-Noir.dmg" \
  "dist/SpiderMan-Not-Noir.app"
```

### Option 3: Homebrew Cask (for wider distribution)

Create a homebrew formula for easy installation:
```bash
brew install --cask spiderman-not-noir
```

## Installation Instructions for End Users

### macOS

1. Download `SpiderMan-Not-Noir-macOS-arm64.zip`
2. Unzip the file
3. Move `SpiderMan-Not-Noir.app` to `/Applications/`
4. **First launch**: Right-click → Open (to bypass Gatekeeper)
5. Grant camera permission when prompted

### Troubleshooting

**"App is damaged and can't be opened"**
```bash
xattr -cr /Applications/SpiderMan-Not-Noir.app
```

**Camera permission issues**
- System Preferences → Privacy & Security → Camera → Enable for SpiderMan-Not-Noir

## Build Script

A convenience build script is provided:

```bash
./build.sh
```

This script:
1. Cleans previous builds
2. Ensures data directory exists
3. Runs PyInstaller with all required options
4. Outputs build location

## Requirements File

For users who want to run from source instead:

```bash
# Clone repository
git clone <repo-url>
cd spiderman-not-noir

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run game
python game.py
```

## Known Issues

1. **Build time**: First build takes 3-5 minutes due to torch analysis
2. **Code signing**: App is not signed, requires Gatekeeper bypass
3. **Universal binary**: Currently ARM64 only (M1/M2 Macs)

## Future Improvements

1. Add code signing for seamless installation
2. Create universal binary (ARM64 + x86_64)
3. Set up GitHub Actions for automated builds
4. Create Windows build with equivalent process

## Consequences

### Positive
- Users don't need Python installed
- Simple double-click to run
- All dependencies bundled
- Professional app bundle with camera permissions

### Negative
- Large file size (~205MB)
- Build requires all dependencies installed
- No auto-update mechanism
- Platform-specific builds needed

## References

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller macOS Bundles](https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle)
- [MediaPipe PyInstaller Hook](https://github.com/pyinstaller/pyinstaller-hooks-contrib)
