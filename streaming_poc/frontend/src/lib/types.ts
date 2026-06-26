/**
 * Type definitions for the streaming POC
 */

// Hand landmark point
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface Point2D {
  x: number;
  y: number;
}

// Hand data from backend
export interface HandData {
  detected: boolean;
  landmarks: Point3D[];
  handedness: string;
  gesture: string | null;
  confidence: number;
}

// Pose data from backend
export interface PoseData {
  left_elbow: Point2D | null;
  right_elbow: Point2D | null;
  left_wrist: Point2D | null;
  right_wrist: Point2D | null;
}

// Symbiote ball data
export interface Symbiote {
  id: string;
  x: number;
  y: number;
  size: number;
  progress: number;
}

// Web shot line
export interface WebLine {
  end: Point2D;
  angle: number;
}

// Web shot data
export interface WebShot {
  id: string;
  start: Point2D;
  lines: WebLine[];
  alpha: number;
  created_at: number;
}

// Score data
export interface Score {
  webs_shot: number;
  balls_destroyed: number;
  hits_taken: number;
  combo: number;
}

// THWIP effect data
export interface ThwipEffect {
  x: number;
  y: number;
  created_at: number;
  age?: number;
}

// Full game state from WebSocket (coord_stream.py - full mode)
export interface GameState {
  // Timing for latency measurement
  frame_id: number;
  frame_timestamp: number;
  server_timestamp: number;
  detection_time_ms: number;
  avg_detection_time_ms: number;

  // Game entities
  hand: HandData | null;
  pose: PoseData | null;
  symbiotes: Symbiote[];
  web_shots: WebShot[];

  // Effects
  thwip: ThwipEffect | null;

  // Game state
  score: Score;
  state: string;
  gesture_detected: boolean;
  gesture_name: string | null;

  // Frame dimensions
  frame_width: number;
  frame_height: number;
}

// Lightweight detection data from WebSocket (lightweight_stream.py - fast mode)
export interface LightweightState {
  // Timing
  frame_id: number;
  timestamp: number;
  detection_ms: number;
  avg_detection_ms: number;

  // Detection data only - landmarks as [x, y, z] arrays
  hand: {
    landmarks: [number, number, number][];
    handedness: string;
  } | null;
  
  // Pose - wrists and elbows as [x, y] arrays
  pose: {
    right_wrist: [number, number] | null;
    right_elbow: [number, number] | null;
    left_wrist: [number, number] | null;
    left_elbow: [number, number] | null;
  } | null;
  
  // Gesture detection
  gesture: {
    detected: boolean;
    name: string | null;
    confidence: number;
  };

  // Frame dimensions
  frame_width: number;
  frame_height: number;
}

// Metrics calculated in frontend
export interface Metrics {
  fps: number;
  latency: number;
  frameDrift: number;
  avgDetectionTime: number;
}

// Shared constants (loaded from JSON)
export interface SharedConstants {
  HAND_CONNECTIONS: [number, number][];
  PALM_POLYGON: number[];
  FINGERTIP_INDICES: number[];
  FINGER_MCP_INDICES: number[];
  COLORS: Record<string, string>;
  WEB_SPREAD_ANGLE: number;
  WEB_LINE_COUNT: number;
  WEB_LINE_THICKNESS: number;
  WEB_GLOW_THICKNESS: number;
  HAND_CONNECTOR_THICKNESS: number;
  HAND_LANDMARK_RADIUS: number;
  SYMBIOTE_GLOW_RADIUS_OFFSET: number;
  FRAME_WIDTH: number;
  FRAME_HEIGHT: number;
  GAME_STATES: string[];
}
