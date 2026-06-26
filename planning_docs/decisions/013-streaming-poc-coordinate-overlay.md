# ADR 013: Streaming POC - Coordinate-Based Overlay (Option 2B)

## Status
**PROPOSED** - Proof of Concept

## Date
2026-06-26

## Context

We want to explore options for integrating a React web dashboard with the Spider-Man Web Shooter game. The primary goals are:

1. **Leaderboard display** - Show high scores and player stats
2. **Configuration panel** - Allow users to adjust symbiote difficulty
3. **Live game view** - Potentially embed the camera feed in the browser

### Options Considered

| Option | Description | Performance | Complexity |
|--------|-------------|-------------|------------|
| **1. Subprocess Launch** | React dashboard launches native OpenCV window | ⭐⭐⭐ Best | ⭐ Easy |
| **2A. Full Video Stream** | Backend renders all graphics, streams JPEG | ⭐ Latency | ⭐⭐ Medium |
| **2B. Coordinate Overlay** | Backend streams raw video + JSON coords, frontend renders graphics | ⭐⭐ Good | ⭐⭐⭐ Complex |
| **3. Hybrid** | Native window for play, React for dashboard/stats | ⭐⭐⭐ Best | ⭐⭐ Medium |

### Why Test Option 2B?

We want to validate whether coordinate-based overlay is viable before committing to a full implementation:

- **Lower backend CPU** - No OpenCV drawing, just coordinate extraction
- **Crisp graphics** - Canvas renders vectors, no JPEG compression artifacts
- **Flexible styling** - Can change graphics in React without touching Python
- **Single UI** - Everything in browser (no separate OpenCV window)

### Key Concerns to Validate

1. **Frame sync** - Will video and coordinates drift apart?
2. **Latency** - Is the round-trip delay acceptable for gameplay?
3. **Frontend performance** - Can Canvas render at 60fps?
4. **Duplicate logic** - Is maintaining drawing code in both Python and JS manageable?

## Decision

Implement a **contained, throwaway proof-of-concept** to measure latency and frame drift before committing to a full React app.

### POC Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React App (Vite + Tailwind)                 │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Canvas Layer                                │ │
│  │  - Hand landmarks (from coordinate WebSocket)                  │ │
│  │  - Web lines (from coordinate WebSocket)                       │ │
│  │  - Symbiote balls (from coordinate WebSocket)                  │ │
│  │  - Score UI (React components)                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                         ▲                                          │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  <img> Layer (MJPEG stream)                                    │ │
│  │  - Raw camera feed ONLY (no graphics rendered by backend)      │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                    ▲                           ▲
         MJPEG Stream (video only)    WebSocket (JSON coordinates)
                    │                           │
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                             │
│                                                                     │
│  GET /video/stream          WS /ws/coordinates                      │
│  - cv2.VideoCapture         - frame_id for sync                     │
│  - encode JPEG only         - hand landmarks (21 points)            │
│  - NO drawing               - pose landmarks                        │
│                             - symbiote positions                    │
│                             - web shot data                         │
│                             - score                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Shared Constants Strategy

To avoid duplicate logic for drawing, we use shared constants:

```
shared_constants.py          →  Export to JSON  →  constants.json
(Python: HAND_CONNECTIONS)                         (JS: import)
```

Both Python and JavaScript use the same:
- Hand landmark connection indices
- Palm polygon indices
- Color definitions
- Web spread angles

### Data Payload (~500-800 bytes per frame)

```json
{
  "frame_id": 12345,
  "frame_timestamp": 1703123456789,
  "server_timestamp": 1703123456800,
  "detection_time_ms": 15.2,
  
  "hand": {
    "detected": true,
    "landmarks": [{"x": 0.45, "y": 0.62, "z": -0.02}, ...],
    "handedness": "Right"
  },
  
  "symbiotes": [
    {"id": "sym_001", "x": 0.2, "y": 0.3, "size": 35, "progress": 0.45}
  ],
  
  "web_shots": [
    {"start": {"x": 0.65, "y": 0.6}, "lines": [...], "alpha": 200}
  ],
  
  "score": {
    "webs_shot": 15,
    "balls_destroyed": 8,
    "hits_taken": 3
  },
  
  "state": "TRIGGERED"
}
```

### Success Criteria

| Metric | Acceptable | Ideal |
|--------|------------|-------|
| Frame Drift | < 3 frames | 0-1 frames |
| Latency | < 150ms | < 50ms |
| FPS | > 25 | > 55 |

### Throwaway Strategy

If POC fails:
```bash
rm -rf streaming_poc/
git checkout shared_constants.py
```

Current game code (`web_shooter.py`, `web_shooter_glove.py`) remains **100% untouched**.

## Implementation

### Project Structure

```
streaming_poc/                    # NEW - Proof of Concept (isolated)
├── README.md                     # How to run, what we're testing
├── requirements.txt              # fastapi, uvicorn, websockets
│
├── backend/
│   ├── __init__.py
│   ├── server.py                 # FastAPI app entry point
│   ├── video_stream.py           # MJPEG endpoint (raw camera)
│   └── coord_stream.py           # WebSocket endpoint (JSON coords)
│
└── frontend/                     # React + Vite + Tailwind
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/
        │   ├── GameCanvas.tsx    # Video + canvas overlay
        │   ├── MetricsPanel.tsx  # Latency/FPS display
        │   └── Controls.tsx      # Toggle buttons
        └── lib/
            ├── draw_utils.ts     # Canvas drawing (mirrors graphics_manager.py)
            └── constants.ts      # Shared constants (from JSON)
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Frontend | React 18 + TypeScript | Type safety, component reusability |
| Build | Vite | Fast dev server, modern bundling |
| Styling | Tailwind CSS | Rapid styling, dark theme |
| Backend | FastAPI | Same Python ecosystem as game |
| Server | Uvicorn | ASGI for async WebSocket support |

## Consequences

### Pros
- ✅ Lower backend CPU (no OpenCV drawing during stream)
- ✅ Crisp vector graphics (no JPEG compression on overlays)
- ✅ Flexible frontend styling (CSS animations, themes)
- ✅ Contained POC (can discard without affecting game)
- ✅ Shared constants prevent logic drift

### Cons
- ❌ Frame sync may drift (need buffering solution)
- ❌ More frontend complexity
- ❌ Drawing code in both Python (native) and TypeScript (web)
- ❌ Network latency affects gameplay feel

### Risks
- **High latency** - If > 150ms, gameplay will feel sluggish
- **Frame drift** - If video and coords desync, graphics will "swim"
- **Mobile performance** - Canvas may lag on mobile browsers

## Follow-up Actions

After POC testing:

1. **If latency is good** → Proceed with full React app (leaderboard, config)
2. **If drift is bad** → Implement frame buffering/sync mechanism
3. **If too slow** → Fall back to Option 3 (native OpenCV + React dashboard)

## References

- [FastAPI Streaming Response](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [WebSocket in FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)
- [Canvas API Performance](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
- [Vite + React Setup](https://vitejs.dev/guide/)
