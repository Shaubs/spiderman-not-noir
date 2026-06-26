/**
 * Shared constants for Spider-Man Web Shooter
 * Matching Python implementation exactly
 */

// Frame dimensions
export const FRAME_WIDTH = 1280;
export const FRAME_HEIGHT = 720;

// Hand landmark connections (MediaPipe format) - matches Python graphics_manager.py
export const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],      // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],      // Index
  [0, 9], [9, 10], [10, 11], [11, 12], // Middle
  [0, 13], [13, 14], [14, 15], [15, 16], // Ring
  [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
  [5, 9], [9, 13], [13, 17],           // Palm web pattern
];

// Palm polygon indices for filled area (matches Python: 1, 5, 9, 13, 17, 0)
export const PALM_POLYGON = [1, 5, 9, 13, 17, 0];

// Fingertip indices
export const FINGERTIP_INDICES = [4, 8, 12, 16, 20];

// Colors (BGR in Python → RGB here) - matches Python graphics_manager.py
export const COLORS = {
  // Python: SPIDERMAN_RED = (0, 0, 200) BGR → RGB
  SPIDEY_RED: 'rgb(200, 0, 0)',
  SPIDEY_RED_HEX: '#C80000',
  // Python: SPIDERMAN_BLUE = (200, 50, 50) BGR → RGB  
  SPIDEY_BLUE: 'rgb(50, 50, 200)',
  SPIDEY_BLUE_HEX: '#3232C8',
  // Symbiote colors
  SYMBIOTE_GLOW: 'rgb(30, 20, 30)',      // Dark purple-ish glow
  SYMBIOTE_BODY: 'rgb(15, 15, 15)',      // Near-black
  SYMBIOTE_HIGHLIGHT: 'rgb(100, 100, 120)', // Bright spot
  SYMBIOTE_OUTLINE: 'rgb(40, 40, 40)',   // Wobble outline
  // Web colors
  WEB_GLOW_BLUE: 'rgba(127, 127, 255, 0.5)', // Blue tint outer glow
  WEB_CORE_WHITE: 'rgb(255, 255, 255)',
};

// Hand rendering settings (matches Python graphics_manager.py)
export const HAND_CONNECTOR_THICKNESS = 20;  // Thick red glove (Python uses 20)
export const HAND_LANDMARK_RADIUS = 8;       // Fingertip radius
export const HAND_OTHER_RADIUS = 6;          // Other joint radius

// Web spread configuration (matches Python depth_config.py)
export const WEB_SPREAD_ANGLE = 15;  // Degrees from center line (Python: web_spread_angle=15.0)
export const WEB_LINE_COUNT = 3;     // Number of web lines (center + left + right)

// Game settings (matching symbiote_config.py NORMAL_SYMBIOTE)
export const SYMBIOTE_SPAWN_INTERVAL = 1800; // ms (1.8 seconds)
export const SYMBIOTE_MAX_COUNT = 15;  // Increased since we spawn 3-4 at a time
export const SYMBIOTE_TRAVEL_TIME = 3000; // ms (3.0 seconds)
export const WEB_DURATION = 500; // ms (matches Python config.py web_duration=0.5)
export const THWIP_DURATION = 800; // ms (matches Python graphics_manager ThwipEffect duration=0.8)

// Symbiote config (matching symbiote_config.py NORMAL)
export const SYMBIOTE_START_SIZE = 1;   // Pixels at spawn (far away) - ADR-010
export const SYMBIOTE_END_SIZE = 80;    // Pixels when close
export const HIT_RADIUS_MULTIPLIER = 1.2; // Makes balls easier to hit
export const DESTRUCTION_FADE_TIME = 300; // ms (Python: destruction_fade_time=0.3)

// Wobble config (matching Python depth_config.py DEFAULT_DEPTH)
export const WOBBLE_ENABLED = true;
export const WOBBLE_AMPLITUDE = 20;     // Pixels (Python: wobble_amplitude=20.0)
export const WOBBLE_FREQUENCY = 1;      // Hz - reduced for smoother wobble
export const WOBBLE_DECAY = true;       // Amplitude decreases as approaching

// Infection system config (matching symbiote_config.py)
export const INFECTION_ENABLED = true;
export const INFECTION_RADIUS_MULTIPLIER = 1.5; // Python: grayscale_radius_multiplier=1.5
export const INFECTION_GROW_TIME = 0; // Instant - grayscale is permanent immediately

// Hit marker config (matching Python symbiote_config.py)
export const HIT_MARKER_DURATION = 2000; // ms (Python: hit_marker_duration=2.0)
