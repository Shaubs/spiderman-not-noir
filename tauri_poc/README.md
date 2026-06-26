# Tauri POC - Abandoned

**Status:** Failed / Abandoned  
**Date:** 2026-06-26

## The Plan

Build a native desktop app using Tauri (Rust backend + React/TypeScript frontend) that runs MediaPipe entirely in JavaScript, eliminating the Python dependency.

### Architecture

```
┌─────────────────────────────────────┐
│         Tauri Window                │
│  ┌───────────────────────────────┐  │
│  │   React + TypeScript + Vite   │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  MediaPipe JS (WASM)    │  │  │
│  │  │  Hand Landmark Detection│  │  │
│  │  └─────────────────────────┘  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Canvas 2D Rendering    │  │  │
│  │  │  Game Logic (TS)        │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│         Rust Backend (minimal)      │
└─────────────────────────────────────┘
```

### What Was Implemented

- React + TypeScript + Vite frontend
- MediaPipe Hand Landmarker in JavaScript (WASM)
- Custom gesture detection (Spider-Man pose)
- Game engine with symbiote balls, collision detection
- Web shooting mechanics with 3-line spread
- Grayscale infection system
- State machine for gesture triggering
- THWIP effects

## What Went Wrong

### 1. Web Rendering - Complete Failure

The web shooting effect never rendered. Despite identical logic to Python:

**Python (works):**
```python
cv2.line(frame, (start_x, start_y), (end_x, end_y), color, thickness)
```

**TypeScript (broken):**
```typescript
ctx.beginPath();
ctx.moveTo(x1, y1);
ctx.lineTo(x2, y2);
ctx.stroke();
```

Only the origin point (red circle at wrist) rendered. The actual web lines never appeared.

### 2. Debugging Difficulty

- Browser console logs not visible in terminal
- Required opening DevTools in Tauri window
- Hot reload sometimes didn't reflect changes
- Multiple processes (Vite + Cargo) complicated debugging

### 3. Complexity Overhead

- ~3x more code than Python for same functionality
- React lifecycle management in animation loops
- Multiple coordinate systems (normalized vs pixel)
- useRef/useCallback patterns for mutable state

## Lessons Learned

1. **Don't rewrite working code** - Python OpenCV works perfectly
2. **Canvas 2D ≠ OpenCV** - Different state management and rendering behavior
3. **Debugging matters** - `print()` beats browser DevTools for rapid iteration
4. **Complexity budget** - More abstraction layers = more failure points

## Recommendation

Use **PyInstaller** to package the Python app as a standalone executable:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## See Also

- `planning_docs/decisions/016-tauri-poc-postmortem.md` - Full ADR
- `planning_docs/decisions/014-tauri-react-architecture.md` - Original design
- `planning_docs/decisions/015-streaming-poc-postmortem.md` - Previous failed attempt
