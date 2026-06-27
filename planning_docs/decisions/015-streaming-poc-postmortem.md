# ADR 015: Streaming POC Postmortem - Why WebSocket + MJPEG Failed

## Status
**Accepted** - 2026-06-26

## Context

We attempted to build a web-based Spider-Man gesture detection game using a streaming architecture:
- **Backend**: Python + FastAPI with WebSocket and MJPEG streaming
- **Frontend**: React running in a browser
- **Video**: MJPEG over HTTP for camera feed
- **Data**: WebSocket for gesture detection results

The goal was to leverage browser-based deployment for cross-platform compatibility.

## Architecture That Was Tried

```
┌─────────────┐     HTTP/MJPEG      ┌─────────────┐
│   Camera    │ ───────────────────▶│   Browser   │
│  (OpenCV)   │                     │   (React)   │
└─────────────┘     WebSocket       └─────────────┘
       │        ◀───────────────▶          │
       ▼              JSON                 ▼
┌─────────────┐                     ┌─────────────┐
│  MediaPipe  │                     │   Canvas    │
│  Detection  │                     │  Rendering  │
└─────────────┘                     └─────────────┘
```

## Problems Encountered

### 1. MJPEG Latency: 100-300ms Delay
- **Root Cause**: JPEG encoding on backend + HTTP transmission + browser decoding
- **Impact**: Gesture detection felt sluggish and unresponsive
- **User Experience**: Hand movements visually lagged behind reality

### 2. Frame Synchronization Issues
- Video frames and detection data arrived asynchronously
- Detection results didn't match the displayed frame
- Created a "ghost hand" effect where overlays lagged behind video

### 3. Browser Limitations
- Cannot access camera at >30fps reliably via streaming
- No direct GPU access for frame processing
- Additional browser security restrictions on localhost

### 4. Resource Overhead
- Double encoding: Camera → OpenCV → JPEG → HTTP → Browser → Decode
- High CPU usage on the Python backend
- Memory pressure from frame buffering

### 5. MediaPipe Telemetry Errors
- Frequent "failed to upload" errors from MediaPipe
- Process cleanup issues on shutdown
- Zombie processes consuming resources

## Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| End-to-end latency | <50ms | 150-300ms |
| Frame rate | 30fps | 15-25fps |
| Detection sync | <1 frame | 3-5 frames |
| CPU usage | <50% | 70-90% |

## Decision

**Abandon the streaming POC** in favor of a **Tauri + Python sidecar** architecture.

### Why Tauri?

1. **Zero streaming latency**: Camera → Canvas directly in the WebView
2. **Native performance**: Rust backend, OS-native WebView
3. **Better IPC**: stdin/stdout JSON-L is faster than WebSocket
4. **Smaller footprint**: 5-15MB vs 150MB+ Electron
5. **Single process model**: Python runs as sidecar, not server

## Consequences

### Positive
- Dramatically reduced latency (<16ms for video)
- Better frame synchronization
- Simpler architecture (no HTTP server needed)
- Distributable as a native app

### Negative
- Not web-deployable (requires desktop app install)
- More complex build process (Rust + Node + Python)
- macOS/Windows/Linux builds needed separately

### Neutral
- React code largely reusable
- Game logic unchanged
- Detection code stays the same

## Lessons Learned

1. **Streaming video to browsers has inherent latency** - avoid for real-time interactive apps
2. **MJPEG is a poor choice** for low-latency applications
3. **WebSocket alone is fine** for data, but not for video
4. **Native apps beat web apps** for camera-intensive applications
5. **Test latency early** - we should have measured this before building features

## Files Removed

```
streaming_poc/
├── backend/
│   ├── app.py              # FastAPI server
│   ├── lightweight_stream.py  # MJPEG + WS endpoint
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── lib/           # Game engine, hooks
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## References

- [ADR 014: Tauri + React Architecture](./014-tauri-react-architecture.md) - The replacement architecture
- [WebRTC vs MJPEG comparison](https://webrtc.org/) - Alternative we considered
- [Tauri Documentation](https://tauri.app/) - Framework we chose instead
