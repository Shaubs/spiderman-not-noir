"""
MJPEG Video Streamer - Raw camera feed without graphics.
Provides frame data for both streaming and coordinate extraction.
"""
import cv2
import time
from typing import Generator, Optional, Tuple
import numpy as np


class VideoStreamer:
    """
    Handles video capture and MJPEG streaming.
    Provides raw frames to CoordinateStreamer for detection.
    """
    
    def __init__(self, camera_id: int = 0, width: int = 1280, height: int = 720):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_id: int = 0
        self.current_frame: Optional[np.ndarray] = None
        self.last_frame_time: float = 0
        self.is_running: bool = False
        
        # Performance metrics
        self.fps_samples: list[float] = []
        self.avg_fps: float = 0
    
    def start(self) -> bool:
        """Start video capture."""
        if self.cap is not None:
            return True
        
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print(f"❌ Failed to open camera {self.camera_id}")
            self.cap = None
            return False
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Try to set higher FPS
        self.cap.set(cv2.CAP_PROP_FPS, 60)
        
        self.is_running = True
        print(f"✅ Camera started: {self.width}x{self.height}")
        return True
    
    def stop(self):
        """Stop video capture."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self.is_running = False
            print("📷 Camera stopped")
    
    def get_frame(self) -> Tuple[Optional[np.ndarray], int, float]:
        """
        Get current frame for coordinate extraction.
        Returns: (frame, frame_id, timestamp)
        """
        if self.cap is None:
            return None, 0, 0
        
        ret, frame = self.cap.read()
        
        if ret:
            self.frame_id += 1
            self.current_frame = frame
            self.last_frame_time = time.time()
            
            # Track FPS
            now = time.time()
            self.fps_samples.append(now)
            self.fps_samples = [t for t in self.fps_samples if now - t < 1.0]
            self.avg_fps = len(self.fps_samples)
        
        return self.current_frame, self.frame_id, self.last_frame_time
    
    def generate_frames(self) -> Generator[bytes, None, None]:
        """
        Generate MJPEG frames for streaming.
        No graphics are drawn - raw camera feed only.
        """
        if not self.start():
            return
        
        jpeg_quality = [cv2.IMWRITE_JPEG_QUALITY, 80]
        
        while self.is_running:
            frame, frame_id, timestamp = self.get_frame()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Flip horizontally for mirror effect (natural for user)
            frame = cv2.flip(frame, 1)
            
            # Encode as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame, jpeg_quality)
            
            if not ret:
                continue
            
            # Yield MJPEG frame with metadata headers
            yield (
                b'--frame\r\n'
                b'X-Frame-ID: ' + str(frame_id).encode() + b'\r\n'
                b'X-Timestamp: ' + f'{timestamp:.6f}'.encode() + b'\r\n'
                b'X-FPS: ' + str(int(self.avg_fps)).encode() + b'\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                jpeg.tobytes() + b'\r\n'
            )
    
    @property
    def frame_shape(self) -> Tuple[int, int]:
        """Return (width, height) of frames."""
        return (self.width, self.height)
