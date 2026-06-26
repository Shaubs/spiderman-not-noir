/**
 * Type definitions for Spider-Man Tauri App
 */

// 3D point (hand landmark)
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

// 2D point
export interface Point2D {
  x: number;
  y: number;
}

// Hand detection data from Python
export interface HandData {
  detected: boolean;
  landmarks: [number, number, number][] | null; // [x, y, z]
  handedness: string;
}

// Pose data from Python
export interface PoseData {
  right_wrist: [number, number] | null;
  right_elbow: [number, number] | null;
  left_wrist: [number, number] | null;
  left_elbow: [number, number] | null;
}

// Gesture data from Python
export interface GestureData {
  name: string | null;
  confidence: number;
  is_spiderman: boolean;
}

// Detection event from Python
export interface DetectionEvent {
  type: 'detection';
  timestamp: number;
  detection_ms: number;
  hand: HandData | null;
  pose: PoseData | null;
  gesture: GestureData;
  state: string;
  trigger_fired: boolean;
}

// Frame event from Python
export interface FrameEvent {
  type: 'frame';
  data: string; // base64
  timestamp: number;
}

// Stats event from Python
export interface StatsEvent {
  type: 'stats';
  fps: number;
  frame_width: number;
  frame_height: number;
}

// Symbiote ball (game entity)
export interface SymbioteBall {
  id: string;
  startX: number;
  startY: number;
  targetX: number;
  targetY: number;
  createdAt: number;
  travelTime: number;
  startSize: number;
  endSize: number;
  wobblePhase: number;
  isDestroyed: boolean;
  currentX?: number;
  currentY?: number;
  currentSize?: number;
}

// Web shot (game entity)
export interface WebShot {
  id: string;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  angle: number;
  createdAt: number;
  alpha: number;
}

// Game score
export interface GameScore {
  websShot: number;
  ballsDestroyed: number;
  hitsTaken: number;
  combo: number;
}

// Complete game state
export interface GameState {
  balls: SymbioteBall[];
  webShots: WebShot[];
  score: GameScore;
  triggerState: 'LOOKING' | 'DETECTED' | 'TRIGGERED' | 'COOLDOWN';
  thwip: { x: number; y: number; createdAt: number } | null;
}
