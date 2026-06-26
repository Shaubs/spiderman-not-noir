/**
 * Shared constants for Spider-Man Web Shooter
 * Used by both React frontend and Python sidecar
 */

// Frame dimensions
export const FRAME_WIDTH = 1280;
export const FRAME_HEIGHT = 720;

// Hand landmark connections (MediaPipe format)
export const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],      // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],      // Index
  [0, 9], [9, 10], [10, 11], [11, 12], // Middle
  [0, 13], [13, 14], [14, 15], [15, 16], // Ring
  [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
  [5, 9], [9, 13], [13, 17],           // Palm
];

// Palm polygon indices for filled area
export const PALM_POLYGON = [0, 1, 5, 9, 13, 17];

// Fingertip indices
export const FINGERTIP_INDICES = [4, 8, 12, 16, 20];

// Colors
export const COLORS = {
  SPIDEY_RED: '#B71C1C',
  SPIDEY_BLUE: '#1565C0',
  SYMBIOTE_PURPLE: '#4B0082',
  WEB_WHITE: '#FFFFFF',
  GLOW_WHITE: 'rgba(255, 255, 255, 0.3)',
};

// Drawing settings
export const HAND_CONNECTOR_THICKNESS = 3;
export const HAND_LANDMARK_RADIUS = 5;
export const WEB_LINE_THICKNESS = 2;
export const WEB_GLOW_THICKNESS = 6;
export const WEB_SPREAD_ANGLE = 10; // degrees
export const WEB_LINE_COUNT = 3;

// Game settings
export const SYMBIOTE_SPAWN_INTERVAL = 2000; // ms
export const SYMBIOTE_MAX_COUNT = 5;
export const SYMBIOTE_TRAVEL_TIME = 4000; // ms
export const WEB_DURATION = 500; // ms
export const THWIP_DURATION = 500; // ms
export const COLLISION_RADIUS = 0.03; // normalized
