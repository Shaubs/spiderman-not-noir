"""
FastAPI server for Spider-Man Streaming POC.
Serves raw video stream + coordinate WebSocket.

v2: Uses lightweight streamer - game logic moved to React.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import time

from .video_stream import VideoStreamer
from .lightweight_stream import LightweightStreamer

# Paths
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"

# Create FastAPI app
app = FastAPI(
    title="Spider-Man Streaming POC v2",
    description="Lightweight detection stream - game logic in React",
    version="0.2.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared streamers (singleton pattern)
video_streamer = VideoStreamer()
lightweight_streamer = LightweightStreamer(video_streamer)


@app.on_event("startup")
async def startup_event():
    """Initialize video capture on startup."""
    video_streamer.start()
    print("🕷️ Spider-Man Streaming POC v2 started (lightweight mode)!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    video_streamer.stop()
    print("👋 Streaming POC stopped")


@app.get("/")
async def index():
    """Serve the React frontend."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run 'npm run build' in frontend/"}


@app.get("/video/stream")
async def video_stream():
    """
    MJPEG video stream endpoint.
    Returns raw camera feed WITHOUT any graphics overlay.
    """
    return StreamingResponse(
        video_streamer.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws/coordinates")
async def coordinate_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for detection data.
    Sends MINIMAL JSON - just landmarks and gesture detection.
    Game logic (balls, webs, collisions) handled by React.
    """
    await websocket.accept()
    print("📡 WebSocket client connected (lightweight mode)")
    
    try:
        async for state in lightweight_streamer.generate_states():
            try:
                await websocket.send_json(state)
            except RuntimeError as e:
                # Client disconnected - normal behavior
                if "websocket.close" in str(e).lower() or "closed" in str(e).lower():
                    break
                print(f"❌ WebSocket runtime error: {e}")
                break
            except Exception as send_error:
                print(f"❌ WebSocket send error: {type(send_error).__name__}: {send_error}")
                break
    except WebSocketDisconnect:
        print("📡 WebSocket client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("📡 WebSocket connection closed")


@app.get("/api/latency-test")
async def latency_test():
    """
    Endpoint for measuring round-trip latency.
    Returns current server timestamp.
    """
    return {
        "server_time_ms": time.time() * 1000,
        "server_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "video_streaming": video_streamer.is_running,
        "frame_id": video_streamer.frame_id,
    }


# Serve static files from React build
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


# Development: serve from src if dist doesn't exist
DEV_FRONTEND_DIR = BASE_DIR / "frontend"
if not FRONTEND_DIR.exists() and DEV_FRONTEND_DIR.exists():
    print("⚠️ Running in dev mode - frontend not built")
