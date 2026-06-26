# 🕷️ Spider-Man Streaming POC

Proof of concept for coordinate-based video streaming with React overlay.

## Purpose

Test the viability of **Option 2B** architecture:
- Backend sends raw video (MJPEG) + coordinate data (WebSocket JSON)
- Frontend renders all graphics on Canvas overlay
- Measure latency, frame drift, and rendering performance

See: [`planning_docs/decisions/013-streaming-poc-coordinate-overlay.md`](../planning_docs/decisions/013-streaming-poc-coordinate-overlay.md)

## Quick Start

### 1. Install Backend Dependencies

```bash
cd streaming_poc
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Export Shared Constants

```bash
cd ..  # Back to project root
python shared_constants.py
```

### 4. Start Backend (Terminal 1)

```bash
cd streaming_poc
uvicorn backend.server:app --reload --port 8000
```

### 5. Start Frontend Dev Server (Terminal 2)

```bash
cd streaming_poc/frontend
npm run dev
```

### 6. Open Browser

Navigate to: **http://localhost:5173**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React App (Vite)                         │
│  ┌────────────────────────────────────────────────────────┐│
│  │  Canvas Overlay (graphics rendered by React)           ││
│  │  - Hand landmarks                                      ││
│  │  - Symbiote balls                                      ││
│  │  - Web shots                                           ││
│  ├────────────────────────────────────────────────────────┤│
│  │  <img> Video Feed (raw camera, no graphics)            ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
          ▲                              ▲
    MJPEG Stream                   WebSocket JSON
          │                              │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│  GET /video/stream       WS /ws/coordinates                 │
│  (raw camera JPEG)       (landmarks, symbiotes, score)      │
└─────────────────────────────────────────────────────────────┘
```

## What We're Measuring

| Metric | Description | Target |
|--------|-------------|--------|
| **Frame Drift** | Difference between video frame_id and coord frame_id | < 3 frames |
| **Latency** | Time from server to client | < 150ms |
| **Detection Time** | MediaPipe processing time | < 30ms |
| **FPS** | WebSocket messages per second | > 30 |

## Endpoints

| Endpoint | Type | Description |
|----------|------|-------------|
| `GET /video/stream` | MJPEG | Raw camera feed |
| `WS /ws/coordinates` | WebSocket | Game state JSON |
| `GET /api/latency-test` | HTTP | Round-trip timing |
| `GET /api/health` | HTTP | Server health check |

## Frontend Controls

- **Toggle Overlay** - Show/hide canvas graphics
- **Test Latency** - Measure HTTP round-trip time
- **Health Check** - Verify backend is running

## Success Criteria

✅ **PASS** if:
- Latency consistently < 150ms
- Frame drift < 3 frames
- No visible "swimming" of graphics on video

❌ **FAIL** if:
- Latency > 200ms (gameplay feels sluggish)
- Frame drift > 5 frames (graphics noticeably lag)
- Canvas rendering causes UI lag

## Throwing Away

If POC fails, simply delete the folder:

```bash
rm -rf streaming_poc/
git checkout shared_constants.py  # Optional: remove shared constants
```

The main game code (`web_shooter.py`, `web_shooter_glove.py`) is **completely unaffected**.

## Next Steps

After testing:

1. **If PASS** → Proceed with full React app (leaderboard, config)
2. **If borderline** → Implement frame buffering/sync
3. **If FAIL** → Fall back to Option 3 (native OpenCV + React dashboard)

## Files

```
streaming_poc/
├── README.md               # This file
├── requirements.txt        # Python dependencies
│
├── backend/
│   ├── __init__.py
│   ├── server.py           # FastAPI app
│   ├── video_stream.py     # MJPEG streamer
│   └── coord_stream.py     # WebSocket streamer
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── index.css
        ├── components/
        │   ├── GameCanvas.tsx
        │   ├── MetricsPanel.tsx
        │   └── Controls.tsx
        └── lib/
            ├── types.ts
            ├── draw_utils.ts
            └── constants.json
```
