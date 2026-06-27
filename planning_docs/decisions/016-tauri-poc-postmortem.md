# ADR-016: Tauri POC Postmortem - Why It Failed

**Date:** 2026-06-26  
**Status:** Rejected  
**Supersedes:** ADR-014 (Tauri React Architecture)

## Context

After ADR-015 documented the failure of the streaming POC (Python backend + React frontend via WebSocket), we attempted a Tauri-based approach (ADR-014) that would run MediaPipe entirely in JavaScript within a native desktop window.

The goal was to eliminate Python entirely and have a pure TypeScript/Rust desktop application.

## Decision

**The Tauri POC is abandoned.** The Python OpenCV implementation remains the production solution.

## What Was Built

The Tauri POC included:
- React + TypeScript + Vite frontend
- MediaPipe Hand Landmarker running in JavaScript
- Custom gesture detection (Spider-Man pose)
- Game engine with symbiote balls, collision detection
- Web shooting mechanics
- Grayscale infection system
- THWIP effects

## What Worked

1. **Camera access** - WebRTC camera feed worked correctly
2. **MediaPipe JS** - Hand landmark detection worked
3. **Gesture detection** - Spider-Man pose detection worked
4. **Ball spawning** - Symbiote balls spawned and animated correctly
5. **Hand rendering** - Spider-Man glove overlay rendered correctly
6. **State machine** - Trigger detection state machine worked

## What Failed

### 1. Web Rendering - Complete Failure

The web shooting effect never rendered correctly. Despite the code being structurally identical to Python:

**Python (works perfectly):**
```python
cv2.line(frame, (web.start_x, web.start_y), (current_end_x, current_end_y),
         (alpha, alpha, alpha), core_thickness)
```

**TypeScript (doesn't render):**
```typescript
ctx.beginPath();
ctx.moveTo(x1, y1);
ctx.lineTo(currentEndX, currentEndY);
ctx.stroke();
```

The web appeared only as a small red circle at the wrist position. The actual line from wrist to target never rendered, despite:
- Correct coordinate calculations
- Proper canvas context setup
- Verified normalized → pixel coordinate conversion

### 2. Debugging Difficulty

Unlike Python where you can simply `print()` and see output immediately, debugging the Tauri app required:
- Opening DevTools in the Tauri window
- Or piping browser console to terminal (not straightforward)
- Hot reload sometimes didn't reflect changes
- Multiple processes (Vite + Cargo) made it hard to trace issues

### 3. Coordinate System Complexity

The TypeScript implementation used normalized coordinates (0-1) throughout, converting to pixels only at render time. This added complexity compared to Python's straightforward pixel coordinates.

### 4. Architecture Overhead

The Tauri POC required managing:
- React component lifecycle
- useRef for mutable state in animation loops
- useCallback for stable function references
- Multiple coordinate systems (normalized, pixel, canvas)
- Async initialization of MediaPipe

The Python version is ~500 lines of straightforward procedural code.

## Root Cause Analysis

The exact root cause of the web rendering failure was never determined. Possible issues:

1. **Canvas state not being saved/restored** - Drawing operations may have been affected by prior context state
2. **Z-order issues** - Web may have been drawn but covered by subsequent drawings
3. **Coordinate calculation errors** - Despite verification, there may have been subtle bugs in normalized → pixel conversion
4. **Timing issues** - React's render cycle may have interfered with canvas drawing

## Lessons Learned

1. **Don't fix what isn't broken** - The Python OpenCV implementation works perfectly. The motivation to rewrite in TypeScript was not justified by actual problems.

2. **Canvas 2D is not cv2** - While conceptually similar, HTML5 Canvas has different behavior around state management, coordinate systems, and rendering pipelines.

3. **Debugging overhead matters** - The ease of `print()` debugging in Python vs browser DevTools in a Tauri window significantly impacts development velocity.

4. **MediaPipe JS vs Python** - While both work, the Python MediaPipe API is more mature and better documented.

5. **Complexity budget** - The Tauri version required ~3x the code for the same functionality, with worse debuggability.

## Consequences

1. **Python remains the production implementation** - No changes to main.py or related files
2. **Tauri POC code preserved** - For reference and potential future investigation
3. **No further web-based attempts planned** - The streaming POC and Tauri POC both failed
4. **Future packaging** - If desktop distribution is needed, use PyInstaller to package Python directly

## Files Affected

```
tauri_poc/
├── src/
│   ├── components/
│   │   └── GameCanvas.tsx      # Main game component (broken web rendering)
│   ├── lib/
│   │   ├── constants.ts        # Game constants (matched Python)
│   │   ├── drawUtils.ts        # Canvas drawing (web rendering broken)
│   │   ├── gameEngine.ts       # Game logic (worked correctly)
│   │   ├── types.ts            # TypeScript types
│   │   └── useHandDetection.ts # MediaPipe hook (worked)
│   └── App.tsx
├── src-tauri/                  # Rust backend (minimal, worked)
├── public/
│   └── thwip.png              # THWIP effect image
└── package.json
```

## Recommendation

**Use PyInstaller for distribution:**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

This creates a standalone Mac/Windows/Linux executable without requiring users to install Python or dependencies.

## References

- ADR-014: Tauri React Architecture (initial design)
- ADR-015: Streaming POC Postmortem (previous failure)
- Python implementation: main.py, web_renderer.py, graphics_manager.py
