/**
 * Canvas drawing utilities for Spider-Man graphics
 * Matches Python implementation exactly
 */

import type { MutableRefObject } from 'react';
import * as C from './constants';
import { SymbioteBall, WebShot } from './types';

/**
 * Clear the canvas
 */
export function clearCanvas(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.clearRect(0, 0, width, height);
}

/**
 * Draw Spider-Man style hand as filled red glove
 * Matches Python graphics_manager.py draw_spiderman_hand_filled EXACTLY
 * 
 * - Filled red palm polygon (indices: 1, 5, 9, 13, 17, 0)
 * - Thick red connectors (20px) - the glove
 * - NO landmark dots visible - solid glove appearance
 */
export function drawSpidermanHand(
  ctx: CanvasRenderingContext2D,
  landmarks: [number, number, number][],
  width: number,
  height: number
) {
  if (landmarks.length < 21) return;
  
  // Get pixel coordinates (same as Python)
  const pts = landmarks.map(lm => [
    Math.floor(lm[0] * width),
    Math.floor(lm[1] * height)
  ]);
  
  // Fill palm polygon (indices: 1, 5, 9, 13, 17, 0) - matches Python exactly
  ctx.fillStyle = C.COLORS.SPIDEY_RED;
  ctx.beginPath();
  ctx.moveTo(pts[C.PALM_POLYGON[0]][0], pts[C.PALM_POLYGON[0]][1]);
  for (let i = 1; i < C.PALM_POLYGON.length; i++) {
    ctx.lineTo(pts[C.PALM_POLYGON[i]][0], pts[C.PALM_POLYGON[i]][1]);
  }
  ctx.closePath();
  ctx.fill();
  
  // Draw connectors - thick red lines (20px like Python)
  ctx.strokeStyle = C.COLORS.SPIDEY_RED;
  ctx.lineWidth = C.HAND_CONNECTOR_THICKNESS; // 20px
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  
  for (const [start, end] of C.HAND_CONNECTIONS) {
    const startPt = pts[start];
    const endPt = pts[end];
    if (startPt && endPt) {
      ctx.beginPath();
      ctx.moveTo(startPt[0], startPt[1]);
      ctx.lineTo(endPt[0], endPt[1]);
      ctx.stroke();
    }
  }
}

/**
 * Draw symbiote ball (matches Python symbiote.py _render_ball EXACTLY)
 * 
 * Visual layers:
 * 1. Dark purple-ish glow (outer ring)
 * 2. Near-black main body
 * 3. Single highlight spot at upper-left
 * 4. Wobble ellipse outline (only for size >= 10)
 */
export function drawSymbiote(
  ctx: CanvasRenderingContext2D,
  ball: SymbioteBall & { progress?: number },
  width: number,
  height: number
) {
  const x = (ball.currentX ?? ball.startX) * width;
  const y = (ball.currentY ?? ball.startY) * height;
  const size = ball.currentSize ?? 20;
  const now = Date.now();
  
  if (ball.isDestroyed) {
    // Destruction animation - 4 splattering particles (like Python)
    const destroyedAt = ball.createdAt + ball.travelTime;
    const destructionAge = now - destroyedAt;
    const progress = Math.min(1, destructionAge / C.DESTRUCTION_FADE_TIME);
    const alpha = 1 - progress;
    
    // Draw 4 splattering particles (reduced from 8 in Python)
    for (let i = 0; i < 4; i++) {
      const angle = (i * Math.PI / 2) + progress * Math.PI;
      const offset = progress * size * 0.8;
      const px = x + Math.cos(angle) * offset;
      const py = y + Math.sin(angle) * offset;
      const particleSize = Math.max(3, size * 0.3 * (1 - progress));
      
      ctx.fillStyle = `rgba(60, 60, 60, ${alpha})`;
      ctx.beginPath();
      ctx.arc(px, py, particleSize, 0, Math.PI * 2);
      ctx.fill();
    }
    
    // Fading center
    const splatSize = size * (1 + progress * 0.5);
    ctx.fillStyle = `rgba(50, 50, 50, ${alpha})`;
    ctx.beginPath();
    ctx.arc(x, y, splatSize / 2, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  
  // OPTIMIZED: Simplified jelly ball (3 draw calls like Python)
  
  // 1. Main body with glow effect (dark purple-ish glow)
  ctx.fillStyle = 'rgb(30, 20, 30)';
  ctx.beginPath();
  ctx.arc(x, y, size + 3, 0, Math.PI * 2);
  ctx.fill();
  
  // Main black body
  ctx.fillStyle = 'rgb(15, 15, 15)';
  ctx.beginPath();
  ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fill();
  
  // 2. Single highlight (combined reflection spot) - only for larger balls
  if (size >= 6) {
    const highlightX = x - size * 0.25;
    const highlightY = y - size * 0.25;
    const highlightSize = Math.max(2, size * 0.25);
    ctx.fillStyle = 'rgb(100, 100, 120)';
    ctx.beginPath();
    ctx.arc(highlightX, highlightY, highlightSize, 0, Math.PI * 2);
    ctx.fill();
  }
  
  // 3. Wobble outline (only for larger balls) - ellipse effect
  if (size >= 10) {
    const wobble = Math.sin((now / 100) + ball.createdAt) * 2;
    const axisW = Math.max(1, size + wobble);
    const axisH = Math.max(1, size - wobble);
    
    ctx.strokeStyle = 'rgb(40, 40, 40)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(x, y, axisW, axisH, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
}

/**
 * Draw web shot (matches Python web_renderer.py _render_web EXACTLY)
 * 
 * Python draws 3 lines per WebShot. In our architecture, we create 3 separate
 * WebShot objects (left, center, right), so each call draws ONE line.
 * 
 * Features:
 * - Web extends outward from wrist to edge of screen
 * - Outer glow (blue tint) + Core (white) + Bright center
 * - Origin point with RED dot and glow (Python uses BGR: 0,0,alpha = RED)
 * - Thickness decreases with progress
 */
export function drawWebShot(
  ctx: CanvasRenderingContext2D,
  web: WebShot,
  width: number,
  height: number
) {
  const now = Date.now();
  const age = now - web.createdAt;
  
  // Progress: 0 = just fired, 1 = fully extended/expired
  const progress = Math.min(1, age / C.WEB_DURATION);
  
  // Opacity: Python uses web.opacity which is (1 - (age/duration)**0.5)
  const opacity = Math.max(0, 1 - Math.pow(age / C.WEB_DURATION, 0.5));
  
  // Debug log
  console.log('🎨 drawWebShot:', { startX: web.startX, startY: web.startY, endX: web.endX, endY: web.endY, progress, opacity });
  
  // Skip if faded out
  if (opacity <= 0.01) return;
  
  // Alpha as integer 0-255 like Python
  const alpha = Math.floor(opacity * 255);
  
  // Convert normalized to pixel coordinates
  const x1 = Math.floor(web.startX * width);
  const y1 = Math.floor(web.startY * height);
  const fullEndX = Math.floor(web.endX * width);
  const fullEndY = Math.floor(web.endY * height);
  
  // Web extends outward based on progress
  const currentEndX = Math.floor(x1 + (fullEndX - x1) * progress);
  const currentEndY = Math.floor(y1 + (fullEndY - y1) * progress);
  
  // Thickness decreases with progress (matches Python exactly)
  const glowThickness = Math.max(1, Math.floor(8 * (1 - progress * 0.5)));
  const coreThickness = Math.max(1, Math.floor(4 * (1 - progress * 0.5)));
  
  // 1. Outer glow (blue tint - Python BGR: alpha//2, alpha//2, alpha → RGB same)
  ctx.strokeStyle = `rgb(${alpha >> 1}, ${alpha >> 1}, ${alpha})`;
  ctx.lineWidth = glowThickness;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(currentEndX, currentEndY);
  ctx.stroke();
  
  // 2. Core line (white - Python: alpha, alpha, alpha)
  ctx.strokeStyle = `rgb(${alpha}, ${alpha}, ${alpha})`;
  ctx.lineWidth = coreThickness;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(currentEndX, currentEndY);
  ctx.stroke();
  
  // 3. Bright center (pure white, only if thick enough)
  if (coreThickness > 2) {
    ctx.strokeStyle = 'rgb(255, 255, 255)';
    ctx.lineWidth = Math.max(1, Math.floor(coreThickness / 2));
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(currentEndX, currentEndY);
    ctx.stroke();
  }
  
  // Origin point with glow (at wrist position)
  // Python: web.thickness = max(1, int(base_thickness * (1 - progress * 0.8)))
  const baseThickness = 5; // ACTIVE_CONFIG.web_thickness default
  const thickness = Math.max(1, Math.floor(baseThickness * (1 - progress * 0.8)));
  
  // Outer glow (Python BGR: alpha//3, alpha//3, alpha//2)
  ctx.fillStyle = `rgb(${Math.floor(alpha / 3)}, ${Math.floor(alpha / 3)}, ${Math.floor(alpha / 2)})`;
  ctx.beginPath();
  ctx.arc(x1, y1, thickness + 4, 0, Math.PI * 2);
  ctx.fill();
  
  // RED origin point (Python BGR: 0, 0, alpha → RGB: alpha, 0, 0 = RED!)
  ctx.fillStyle = `rgb(${alpha}, 0, 0)`;
  ctx.beginPath();
  ctx.arc(x1, y1, thickness + 2, 0, Math.PI * 2);
  ctx.fill();
  
  // White highlight on origin
  ctx.fillStyle = `rgb(${alpha}, ${alpha}, ${alpha})`;
  ctx.beginPath();
  ctx.arc(x1 - 2, y1 - 2, Math.floor(thickness / 2), 0, Math.PI * 2);
  ctx.fill();
}

// THWIP image cache (loaded once, reused)
let thwipImage: HTMLImageElement | null = null;
let thwipImageLoading = false;
let thwipImageLoaded = false;

/**
 * Load THWIP PNG image (call once at startup)
 */
export function loadThwipImage(): Promise<void> {
  if (thwipImageLoaded || thwipImageLoading) return Promise.resolve();
  
  thwipImageLoading = true;
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      thwipImage = img;
      thwipImageLoaded = true;
      thwipImageLoading = false;
      console.log('✅ THWIP image loaded:', img.width, 'x', img.height);
      resolve();
    };
    img.onerror = () => {
      console.warn('⚠️ THWIP image failed to load, using text fallback');
      thwipImageLoading = false;
      resolve();
    };
    img.src = '/thwip.png';
  });
}

/**
 * Draw THWIP effect using PNG image (matches Python graphics_manager.py)
 * 
 * Shows at COLLISION POINT (where web destroyed ball)
 * Animation: starts at 0.8 scale → shrinks to 0.3 as it fades
 * Uses PNG image with alpha blending
 */
export function drawThwip(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  age: number,
  width: number,
  height: number
) {
  const pixelX = x * width;
  const pixelY = y * height;
  
  // Progress 0 = just fired, 1 = expired
  const progress = Math.min(1, age / C.THWIP_DURATION);
  const alpha = Math.max(0, 1 - progress);
  
  // Skip if fully faded
  if (alpha <= 0.01) return;
  
  // Scale animation (matches Python exactly)
  // Python: if progress < 0.3: scale=0.8, elif progress < 0.6: scale=0.5, else: scale=0.3
  let scale: number;
  if (progress < 0.3) {
    scale = 0.8;
  } else if (progress < 0.6) {
    scale = 0.5;
  } else {
    scale = 0.3;
  }
  
  ctx.save();
  ctx.globalAlpha = alpha;
  
  // If image loaded, use it
  if (thwipImage && thwipImageLoaded) {
    const imgWidth = thwipImage.width * scale;
    const imgHeight = thwipImage.height * scale;
    
    // Center image on collision point
    const drawX = pixelX - imgWidth / 2;
    const drawY = pixelY - imgHeight / 2;
    
    ctx.drawImage(thwipImage, drawX, drawY, imgWidth, imgHeight);
  } else {
    // Fallback to text if image not loaded
    ctx.translate(pixelX, pixelY);
    ctx.scale(scale, scale);
    
    ctx.font = 'bold 72px "Comic Sans MS", "Bangers", Impact, cursive';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // Black outline
    ctx.strokeStyle = 'black';
    ctx.lineWidth = 8;
    ctx.strokeText('THWIP!', 0, 0);
    
    // Yellow fill
    ctx.fillStyle = 'rgb(255, 220, 0)';
    ctx.fillText('THWIP!', 0, 0);
  }
  
  ctx.restore();
}

/**
 * Draw state indicator pill
 */
export function drawStateIndicator(
  ctx: CanvasRenderingContext2D,
  state: string,
  gestureDetected: boolean,
  width: number
) {
  const stateColors: Record<string, string> = {
    'LOOKING': '#888888',
    'DETECTED': '#FFD700',
    'TRIGGERED': '#00FF00',
    'COOLDOWN': '#4FC3F7',
  };
  
  const color = stateColors[state] || '#888888';
  
  // State pill at top center
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  const pillWidth = 150;
  const pillHeight = 30;
  const pillX = (width - pillWidth) / 2;
  const pillY = 10;
  
  ctx.beginPath();
  ctx.roundRect(pillX, pillY, pillWidth, pillHeight, 15);
  ctx.fill();
  
  // State text
  ctx.fillStyle = color;
  ctx.font = 'bold 16px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(state, width / 2, pillY + 21);
  
  // Gesture indicator dot
  if (gestureDetected) {
    ctx.fillStyle = '#00FF00';
    ctx.beginPath();
    ctx.arc(pillX + 20, pillY + pillHeight / 2, 6, 0, Math.PI * 2);
    ctx.fill();
  }
}

/**
 * Draw score panel
 */
export function drawScore(
  ctx: CanvasRenderingContext2D,
  score: { websShot: number; ballsDestroyed: number; hitsTaken: number; combo: number },
  height: number
) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(10, height - 70, 200, 60);
  
  ctx.font = '14px monospace';
  ctx.textAlign = 'left';
  
  ctx.fillStyle = '#FFD700';
  ctx.fillText(`Webs: ${score.websShot}`, 20, height - 48);
  ctx.fillText(`Hits: ${score.ballsDestroyed}`, 20, height - 28);
  
  ctx.fillStyle = '#FF4444';
  ctx.fillText(`Taken: ${score.hitsTaken}`, 120, height - 48);
  
  ctx.fillStyle = '#00FF00';
  ctx.fillText(`Combo: ${score.combo}`, 120, height - 28);
}

/**
 * Apply PERMANENT grayscale effect to infected zones
 * Matches Python symbiote.py render_grayscale_effect EXACTLY
 * 
 * Key behaviors:
 * - Grayscale is PERMANENT - once infected, stays forever until game reset
 * - Uses cached boolean mask for efficiency
 * - Only rebuilds mask when new zones added
 * - Skips already-gray pixels (optimization)
 * 
 * @param grayscaleMaskRef - Persistent mask ref that survives across frames
 * @param lastProcessedZoneCountRef - Tracks how many zones we've processed
 */
export function applyPermanentGrayscale(
  ctx: CanvasRenderingContext2D,
  zones: Array<{ x: number; y: number; radius: number; createdAt: number }>,
  width: number,
  height: number,
  grayscaleMaskRef: MutableRefObject<Uint8Array | null>,
  lastProcessedZoneCountRef: MutableRefObject<number>
) {
  const pixelCount = width * height;
  
  // Initialize mask if needed
  if (!grayscaleMaskRef.current || grayscaleMaskRef.current.length !== pixelCount) {
    grayscaleMaskRef.current = new Uint8Array(pixelCount);
    lastProcessedZoneCountRef.current = 0;
  }
  
  const mask = grayscaleMaskRef.current;
  
  // Only process NEW zones (optimization like Python _mask_dirty flag)
  const newZoneCount = zones.length;
  const startIdx = lastProcessedZoneCountRef.current;
  
  // Process new zones to update the mask
  for (let i = startIdx; i < newZoneCount; i++) {
    const zone = zones[i];
    
    // Convert normalized coordinates to pixel coordinates
    const cx = Math.floor(zone.x * width);
    const cy = Math.floor(zone.y * height);
    
    // FIXED: radius is stored as normalized value: (endSize * multiplier) / FRAME_WIDTH
    // Python stores it as pixels directly: int(ball.end_size * config.grayscale_radius_multiplier)
    // So we need to multiply by FRAME_WIDTH to get pixels back
    // zone.radius = (80 * 1.5) / 1280 ≈ 0.09375
    // radiusPx = 0.09375 * 1280 = 120 pixels
    const radiusPx = Math.floor(zone.radius * C.FRAME_WIDTH);
    
    // Ensure minimum visible radius
    if (radiusPx < 5) continue;
    
    const radiusSq = radiusPx * radiusPx;
    
    // Only check pixels within bounding box (optimization like Python)
    const minX = Math.max(0, cx - radiusPx);
    const maxX = Math.min(width - 1, cx + radiusPx);
    const minY = Math.max(0, cy - radiusPx);
    const maxY = Math.min(height - 1, cy + radiusPx);
    
    // Mark all pixels within radius as permanently infected
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        const idx = y * width + x;
        // Skip if already infected (Python optimization)
        if (mask[idx] === 1) continue;
        
        const dx = x - cx;
        const dy = y - cy;
        if (dx * dx + dy * dy <= radiusSq) {
          mask[idx] = 1;
        }
      }
    }
  }
  
  // Update processed count
  lastProcessedZoneCountRef.current = newZoneCount;
  
  // Apply grayscale using the permanent mask
  applyExistingGrayscaleMask(ctx, mask, width, height);
}

/**
 * Apply grayscale effect using an existing mask
 * Matches Python symbiote.py render_grayscale_effect
 * 
 * Uses bounding box optimization: only convert affected ROI to grayscale
 */
export function applyExistingGrayscaleMask(
  ctx: CanvasRenderingContext2D,
  mask: Uint8Array,
  width: number,
  height: number
) {
  // Get the full canvas image data
  const imageData = ctx.getImageData(0, 0, width, height);
  const data = imageData.data;
  const pixelCount = width * height;
  
  // Apply grayscale to infected pixels only
  // Matches Python: gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  for (let i = 0; i < pixelCount; i++) {
    if (mask[i] === 1) {
      const idx = i * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      
      // Skip if already grayscale (R ≈ G ≈ B) - optimization
      const maxDiff = Math.max(Math.abs(r - g), Math.abs(g - b), Math.abs(r - b));
      if (maxDiff < 5) continue;
      
      // Luminance formula (standard grayscale conversion)
      // Same as cv2.cvtColor BGR2GRAY
      const gray = Math.floor(0.299 * r + 0.587 * g + 0.114 * b);
      
      // Apply grayscale (symbiote corruption)
      data[idx] = gray;     // R
      data[idx + 1] = gray; // G
      data[idx + 2] = gray; // B
      // Alpha stays unchanged
    }
  }
  
  ctx.putImageData(imageData, 0, 0);
}

/**
 * Check if a point is already in an infected zone
 * Used for spawn optimization (don't spawn where already infected)
 */
export function isPointInfected(
  x: number,
  y: number,
  zones: Array<{ x: number; y: number; radius: number }>
): boolean {
  for (const zone of zones) {
    const dx = x - zone.x;
    const dy = y - zone.y;
    if (dx * dx + dy * dy <= zone.radius * zone.radius) {
      return true;
    }
  }
  return false;
}
