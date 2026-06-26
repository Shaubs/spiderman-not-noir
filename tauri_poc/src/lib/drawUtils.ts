/**
 * Canvas drawing utilities for Spider-Man graphics
 */

import * as C from './constants';
import { SymbioteBall, WebShot } from './types';

/**
 * Clear the canvas
 */
export function clearCanvas(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.clearRect(0, 0, width, height);
}

/**
 * Draw Spider-Man style hand from [x,y,z][] landmarks
 */
export function drawSpidermanHand(
  ctx: CanvasRenderingContext2D,
  landmarks: [number, number, number][],
  width: number,
  height: number
) {
  if (landmarks.length < 21) return;
  
  // Draw connections (red lines between landmarks)
  ctx.strokeStyle = C.COLORS.SPIDEY_RED;
  ctx.lineWidth = C.HAND_CONNECTOR_THICKNESS;
  ctx.lineCap = 'round';
  
  for (const [start, end] of C.HAND_CONNECTIONS) {
    const startLm = landmarks[start];
    const endLm = landmarks[end];
    if (startLm && endLm) {
      ctx.beginPath();
      ctx.moveTo(startLm[0] * width, startLm[1] * height);
      ctx.lineTo(endLm[0] * width, endLm[1] * height);
      ctx.stroke();
    }
  }
  
  // Draw palm polygon (filled red area)
  if (C.PALM_POLYGON.length >= 3) {
    ctx.fillStyle = 'rgba(183, 28, 28, 0.3)';
    ctx.beginPath();
    const firstIdx = C.PALM_POLYGON[0];
    const firstLm = landmarks[firstIdx];
    if (firstLm) {
      ctx.moveTo(firstLm[0] * width, firstLm[1] * height);
      for (let i = 1; i < C.PALM_POLYGON.length; i++) {
        const lm = landmarks[C.PALM_POLYGON[i]];
        if (lm) {
          ctx.lineTo(lm[0] * width, lm[1] * height);
        }
      }
      ctx.closePath();
      ctx.fill();
    }
  }
  
  // Draw landmark points
  for (const lm of landmarks) {
    const x = lm[0] * width;
    const y = lm[1] * height;
    
    // Glow
    ctx.fillStyle = C.COLORS.GLOW_WHITE;
    ctx.beginPath();
    ctx.arc(x, y, C.HAND_LANDMARK_RADIUS + 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Core
    ctx.fillStyle = C.COLORS.SPIDEY_BLUE;
    ctx.beginPath();
    ctx.arc(x, y, C.HAND_LANDMARK_RADIUS, 0, Math.PI * 2);
    ctx.fill();
  }
}

/**
 * Draw symbiote ball
 */
export function drawSymbiote(
  ctx: CanvasRenderingContext2D,
  ball: SymbioteBall,
  width: number,
  height: number
) {
  const x = (ball.currentX ?? ball.startX) * width;
  const y = (ball.currentY ?? ball.startY) * height;
  const size = ball.currentSize ?? 20;
  
  if (ball.isDestroyed) {
    // Explosion effect
    ctx.fillStyle = 'rgba(75, 0, 130, 0.5)';
    ctx.beginPath();
    ctx.arc(x, y, size * 1.5, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  
  // Glow
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, size + 10);
  gradient.addColorStop(0, 'rgba(75, 0, 130, 0.8)');
  gradient.addColorStop(0.5, 'rgba(75, 0, 130, 0.4)');
  gradient.addColorStop(1, 'rgba(75, 0, 130, 0)');
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(x, y, size + 10, 0, Math.PI * 2);
  ctx.fill();
  
  // Core
  ctx.fillStyle = C.COLORS.SYMBIOTE_PURPLE;
  ctx.beginPath();
  ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * Draw web shot
 */
export function drawWebShot(
  ctx: CanvasRenderingContext2D,
  web: WebShot,
  width: number,
  height: number
) {
  const x1 = web.startX * width;
  const y1 = web.startY * height;
  const x2 = web.endX * width;
  const y2 = web.endY * height;
  const alpha = web.alpha / 255;
  
  // Glow
  ctx.strokeStyle = `rgba(150, 150, 255, ${alpha * 0.5})`;
  ctx.lineWidth = C.WEB_GLOW_THICKNESS;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  
  // Main line
  ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
  ctx.lineWidth = C.WEB_LINE_THICKNESS;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

/**
 * Draw THWIP text effect
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
  const alpha = Math.max(0, 1 - age / C.THWIP_DURATION);
  const scale = 1 + age * 0.002;
  
  ctx.save();
  ctx.translate(pixelX, pixelY - 30);
  ctx.scale(scale, scale);
  ctx.font = 'bold 28px Comic Sans MS, cursive';
  ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
  ctx.strokeStyle = `rgba(0, 0, 0, ${alpha})`;
  ctx.lineWidth = 3;
  ctx.textAlign = 'center';
  ctx.strokeText('THWIP!', 0, 0);
  ctx.fillText('THWIP!', 0, 0);
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
