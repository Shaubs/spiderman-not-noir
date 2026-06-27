# ADR 014: Tauri + React + Python Sidecar Architecture

## Status
**Proposed** | Date: 2026-06-26

## Context

### Problem Statement
The streaming POC (ADR 013) revealed fundamental issues with browser-based video streaming:

1. **MJPEG latency**: 100-300ms delay between camera capture and display
2. **Frame sync issues**: Graphics overlay drifts from video frames
3. **Bandwidth overhead**: Uncompressed JPEG frames consume 5-10 Mbps
4. **Camera lock**: Python holds camera, browser cannot access it independently

### Requirements
- **Low latency**: <50ms from gesture to visual feedback
- **Smooth graphics**: 60fps animations for symbiotes, webs, THWIP effects
- **Accurate detection**: MediaPipe hand/pose tracking (Python-only)
- **Rich UI**: React components, Tailwind CSS, modern web tooling

### Options Considered

| Option | Latency | Complexity | Deployment |
|--------|---------|------------|------------|
| MJPEG Streaming (current) | 100-300ms | Low | Web |
| WebRTC | 20-50ms | High | Web |
| Electron + Python | ~0ms | Medium | Desktop |
| **Tauri + Python Sidecar** | **~0ms** | **Medium** | **Desktop** |
| Pure Python/OpenCV | ~0ms | Low | Desktop (no React) |

## Decision

**Adopt Tauri + React + Python Sidecar architecture** for the Spider-Man web shooter application.

### Why Tauri?

1. **Tiny footprint**: ~5-15MB vs 150MB+ Electron
2. **Native WebView**: Uses OS's built-in browser engine (no bundled Chromium)
3. **Rust core**: Fast, safe IPC between frontend and backend
4. **Sidecar support**: First-class support for spawning external processes
5. **Cross-platform**: macOS, Windows, Linux from single codebase

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TAURI APPLICATION                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         WEBVIEW (React + Vite)                         │ │
│  │                                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │  VideoFrame  │  │  GameCanvas  │  │  ScoreBoard  │  │  Controls  │ │ │
│  │  │  <img>       │  │  <canvas>    │  │  Component   │  │  Panel     │ │ │
│  │  │  (base64)    │  │  (overlay)   │  │              │  │            │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  │         ▲                 ▲                                            │ │
│  │         │                 │                                            │ │
│  │  ┌──────┴─────────────────┴──────────────────────────────────────────┐ │ │
│  │  │                        React Hooks                                 │ │ │
│  │  │  useGameEngine()  useDetection()  useTauriEvents()                │ │ │
│  │  └───────────────────────────┬───────────────────────────────────────┘ │ │
│  │                              │                                         │ │
│  │                   invoke() / listen()                                  │ │
│  │                      (Tauri IPC)                                       │ │
│  └──────────────────────────────┼─────────────────────────────────────────┘ │
│                                 │                                            │
│                                 ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         RUST CORE (Tauri)                              │ │
│  │                                                                        │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐│ │
│  │  │ Tauri Commands  │  │ Event Emitter   │  │ Sidecar Manager         ││ │
│  │  │                 │  │                 │  │                         ││ │
│  │  │ start_detector  │  │ emit("frame")   │  │ spawn Python process    ││ │
│  │  │ stop_detector   │  │ emit("detection")│ │ handle stdin/stdout     ││ │
│  │  │ get_settings    │  │ emit("gesture") │  │ restart on crash        ││ │
│  │  └─────────────────┘  └─────────────────┘  └───────────┬─────────────┘│ │
│  │                                                        │              │ │
│  └────────────────────────────────────────────────────────┼──────────────┘ │
│                                                           │                 │
│                              stdout (JSON-L) / stdin      │                 │
│                                                           ▼                 │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      PYTHON SIDECAR                                    │ │
│  │                                                                        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │ │
│  │  │   OpenCV    │  │  MediaPipe  │  │   FFNN      │  │   Gesture    │  │ │
│  │  │   Camera    │  │  Holistic   │  │  Classifier │  │   State      │  │ │
│  │  │   Capture   │  │  Tracker    │  │  (optional) │  │   Machine    │  │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │ │
│  │         │                │                │                │          │ │
│  │         ▼                ▼                ▼                ▼          │ │
│  │  ┌────────────────────────────────────────────────────────────────┐   │ │
│  │  │                    Output to stdout (JSON-L)                   │   │ │
│  │  │  {"type":"frame","data":"base64...","timestamp":1234567890}    │   │ │
│  │  │  {"type":"detection","hand":{...},"pose":{...},"gesture":...}  │   │ │
│  │  └────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
│                                                                              │
│   CAMERA          PYTHON           RUST            REACT                     │
│     │               │                │               │                       │
│     │  capture()    │                │               │                       │
│     ├──────────────▶│                │               │                       │
│     │               │                │               │                       │
│     │               │ MediaPipe      │               │                       │
│     │               │ detect()       │               │                       │
│     │               │◀──────────────▶│               │                       │
│     │               │                │               │                       │
│     │               │ JSON-L stdout  │               │                       │
│     │               ├───────────────▶│               │                       │
│     │               │                │               │                       │
│     │               │                │ emit("frame") │                       │
│     │               │                ├──────────────▶│                       │
│     │               │                │               │ setFrame(base64)      │
│     │               │                │               │◀──────────────────    │
│     │               │                │               │                       │
│     │               │                │emit("detect") │                       │
│     │               │                ├──────────────▶│                       │
│     │               │                │               │ setDetection(data)    │
│     │               │                │               │◀──────────────────    │
│     │               │                │               │                       │
│     │               │                │               │ gameEngine.update()   │
│     │               │                │               │◀──────────────────    │
│     │               │                │               │                       │
│     │               │                │               │ render canvas         │
│     │               │                │               │◀──────────────────    │
│                                                                              │
│   ~30fps capture    ~30fps detect   Event bridge    60fps render             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. React Frontend (WebView)

| Component | Responsibility |
|-----------|----------------|
| `VideoFrame` | Display base64-encoded frames from Python |
| `GameCanvas` | Canvas overlay for hand graphics, symbiotes, webs, THWIP |
| `ScoreBoard` | Display score, combo, stats |
| `Controls` | Settings panel, debug toggles |
| `useGameEngine` | Ball spawning, collision detection, scoring (60fps) |
| `useDetection` | Subscribe to detection events from Rust |
| `useTauriEvents` | Wrapper for Tauri event system |

**Key Point**: Game logic runs in React at 60fps, independent of detection rate.

### 2. Rust Core (Tauri)

| Component | Responsibility |
|-----------|----------------|
| `main.rs` | App initialization, window creation |
| `commands.rs` | Tauri commands (`start_detector`, `stop_detector`) |
| `sidecar.rs` | Python process management (spawn, restart, cleanup) |
| `events.rs` | Parse Python stdout, emit events to React |

**Key Point**: Rust acts as a thin bridge, not processing video data.

### 3. Python Sidecar

| Component | Responsibility |
|-----------|----------------|
| `detector.py` | Main loop: capture → detect → output |
| `holistic_tracker.py` | MediaPipe hand/pose detection (reuse existing) |
| `gesture_classifier.py` | Spider-Man gesture detection (reuse existing) |
| `gesture_state_machine.py` | Trigger detection with debounce (reuse existing) |

**Key Point**: Python only does detection, outputs JSON-L to stdout.

## Communication Protocol

### Python → Rust (stdout, JSON Lines)

```json
{"type":"frame","ts":1234567890123,"data":"base64-encoded-jpeg"}
{"type":"detection","ts":1234567890156,"hand":{"landmarks":[[0.5,0.3,0.1],...],"handedness":"Right"},"pose":{"right_wrist":[0.5,0.6],"right_elbow":[0.4,0.5]},"gesture":{"name":"spiderman","confidence":0.95,"triggered":true}}
{"type":"status","ts":1234567890200,"fps":28.5,"detection_ms":35}
```

### Rust → Python (stdin, JSON Lines)

```json
{"command":"set_fps","value":30}
{"command":"toggle_pose","value":false}
{"command":"shutdown"}
```

### Rust → React (Tauri Events)

```typescript
// React listens for events
listen<FrameEvent>('frame', (event) => {
  setFrame(event.payload.data);
});

listen<DetectionEvent>('detection', (event) => {
  setDetection(event.payload);
});
```

### React → Rust (Tauri Commands)

```typescript
// React invokes commands
await invoke('start_detector');
await invoke('stop_detector');
await invoke('set_setting', { key: 'fps', value: 30 });
```

## Project Structure

```
spiderman-tauri/
├── src/                          # React frontend
│   ├── main.tsx                  # Entry point
│   ├── App.tsx                   # Main app layout
│   ├── components/
│   │   ├── VideoFrame.tsx        # Base64 image display
│   │   ├── GameCanvas.tsx        # Canvas overlay
│   │   ├── ScoreBoard.tsx        # Score display
│   │   └── Controls.tsx          # Settings panel
│   ├── hooks/
│   │   ├── useGameEngine.ts      # Game logic (60fps)
│   │   ├── useDetection.ts       # Detection state
│   │   └── useTauriEvents.ts     # Event subscriptions
│   ├── lib/
│   │   ├── draw_utils.ts         # Canvas drawing (reuse)
│   │   ├── constants.ts          # Shared constants
│   │   └── types.ts              # TypeScript types
│   └── styles/
│       └── index.css             # Tailwind CSS
│
├── src-tauri/                    # Rust backend
│   ├── src/
│   │   ├── main.rs               # Tauri app setup
│   │   ├── commands.rs           # IPC command handlers
│   │   ├── sidecar.rs            # Python process manager
│   │   └── events.rs             # Event parsing/emitting
│   ├── Cargo.toml                # Rust dependencies
│   ├── tauri.conf.json           # Tauri configuration
│   └── icons/                    # App icons
│
├── python/                       # Python sidecar
│   ├── detector.py               # Main detection loop
│   ├── holistic_tracker.py       # Copy from main project
│   ├── gesture_state_machine.py  # Copy from main project
│   ├── config.py                 # Settings
│   └── requirements.txt          # Python deps
│
├── package.json                  # React/Vite dependencies
├── vite.config.ts                # Vite config for Tauri
├── tailwind.config.js            # Tailwind config
├── tsconfig.json                 # TypeScript config
└── README.md                     # Setup instructions
```

## Reusable Code from Existing Project

### From `streaming_poc/frontend/` (React)
- `src/lib/gameEngine.ts` → `src/hooks/useGameEngine.ts`
- `src/lib/draw_utils.ts` → `src/lib/draw_utils.ts`
- `src/lib/types.ts` → `src/lib/types.ts`
- `src/components/GameCanvas.tsx` → Adapt for Tauri events

### From Main Project (Python)
- `holistic_tracker.py` → `python/holistic_tracker.py`
- `gesture_state_machine.py` → `python/gesture_state_machine.py`
- `ffnn_classifier/` → `python/classifier/` (optional)
- `config.py` → `python/config.py`

**Estimated reuse: ~70% of existing code**

## Performance Characteristics

| Metric | Expected Value | Notes |
|--------|----------------|-------|
| Frame capture | ~30fps | OpenCV VideoCapture limit |
| Detection latency | 30-50ms | MediaPipe processing |
| IPC overhead | <5ms | JSON-L over stdin/stdout |
| React render | 60fps | requestAnimationFrame |
| Total latency | <60ms | Capture to display |
| App size | 10-20MB | Tauri + Python bundle |
| Memory usage | ~200-400MB | MediaPipe models |

## Implementation Phases

### Phase 1: Skeleton (1-2 days)
- [ ] Initialize Tauri project with React + Vite
- [ ] Basic Python sidecar that outputs test JSON
- [ ] Rust reads stdout, emits events to React
- [ ] React displays received data

### Phase 2: Video Pipeline (1-2 days)
- [ ] Python captures camera, outputs base64 frames
- [ ] React displays frames in `<img>` element
- [ ] Measure latency, optimize JPEG quality

### Phase 3: Detection Integration (1-2 days)
- [ ] Port HolisticTracker to sidecar
- [ ] Output detection data as JSON-L
- [ ] React receives and renders hand overlay

### Phase 4: Game Logic (2-3 days)
- [ ] Port gameEngine.ts
- [ ] Symbiote spawning and animation
- [ ] Web shooting and collision detection
- [ ] Score tracking

### Phase 5: Polish (1-2 days)
- [ ] Error handling, sidecar restart
- [ ] Settings persistence
- [ ] App packaging (macOS .dmg)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Python packaging complexity | High | Use PyInstaller, test early |
| Base64 frame overhead | Medium | Use lower JPEG quality (60-70%) |
| Sidecar crash handling | Medium | Implement auto-restart in Rust |
| Cross-platform issues | Medium | Test on macOS first, then expand |
| Rust learning curve | Low | Minimal Rust needed, mostly boilerplate |

## Alternatives Not Chosen

### WebRTC
- More complex signaling setup
- Overkill for local-only application
- Debugging is harder

### Electron
- 150MB+ app size
- Higher memory usage
- No native sidecar support

### Pure Python/OpenCV
- Works well (current main.py)
- Limited graphics capabilities
- No modern UI framework

## Success Criteria

1. **Latency**: <60ms from gesture to visual feedback
2. **Smoothness**: 60fps canvas animations
3. **Reliability**: Sidecar auto-restarts on crash
4. **Size**: App bundle <25MB (excluding Python runtime)
5. **Reuse**: >60% code reused from existing project

## References

- [Tauri Documentation](https://tauri.app/v1/guides/)
- [Tauri Sidecar Guide](https://tauri.app/v1/guides/building/sidecar/)
- [aiortc (WebRTC alternative)](https://github.com/aiortc/aiortc)
- [ADR 013: Streaming POC](./013-streaming-poc-coordinate-overlay.md)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-26 | Proposed Tauri architecture | Streaming POC latency issues |
