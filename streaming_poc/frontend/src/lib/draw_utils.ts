/**
 * Drawing utilities for canvas overlay.
 * Mirrors the Python graphics_manager.py for consistency.
 */

import { Point3D, Symbiote, WebShot, SharedConstants } from './types';

/**
 * Draw Spider-Man style hand with filled palm and thick connectors.
 */
export function drawSpidermanHand(
  ctx: CanvasRenderingContext2D,
  landmarks: Point3D[],
  width: number,
  height: number,
  constants: SharedConstants
): void {
  const { HAND_CONNECTIONS, PALM_POLYGON, COLORS, HAND_CONNECTOR_THICKNESS } = constants;

  // Convert normalized coords to pixels
  const points = landmarks.map((lm) => ({
    x: lm.x * width,
    y: lm.y * height,
  }));

  // Fill palm polygon first (background)
  ctx.fillStyle = COLORS.glove_red;
  ctx.beginPath();
  PALM_POLYGON.forEach((idx, i) => {
    const p = points[idx];
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.closePath();
  ctx.fill();

  // Draw connections (thick red lines - glove style)
  ctx.strokeStyle = COLORS.glove_red;
  ctx.lineWidth = HAND_CONNECTOR_THICKNESS;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  HAND_CONNECTIONS.forEach(([start, end]) => {
    const p1 = points[start];
    const p2 = points[end];
    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
  });
}

/**
 * Draw a symbiote ball with gradient glow.
 */
export function drawSymbiote(
  ctx: CanvasRenderingContext2D,
  sym: Symbiote,
  width: number,
  height: number,
  constants: SharedConstants
): void {
  const { COLORS, SYMBIOTE_GLOW_RADIUS_OFFSET } = constants;

  const x = sym.x * width;
  const y = sym.y * height;
  const size = sym.size;

  // Outer glow gradient
  const gradient = ctx.createRadialGradient(
    x, y, 0,
    x, y, size + SYMBIOTE_GLOW_RADIUS_OFFSET
  );
  gradient.addColorStop(0, 'rgba(50, 0, 80, 0.8)');
  gradient.addColorStop(1, 'rgba(20, 0, 40, 0)');

  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(x, y, size + SYMBIOTE_GLOW_RADIUS_OFFSET, 0, Math.PI * 2);
  ctx.fill();

  // Main body
  ctx.fillStyle = COLORS.symbiote_dark;
  ctx.beginPath();
  ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fill();

  // Progress indicator (subtle ring)
  if (sym.progress > 0.1) {
    ctx.strokeStyle = `rgba(255, 0, 100, ${sym.progress * 0.5})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, size + 5, 0, Math.PI * 2 * sym.progress);
    ctx.stroke();
  }
}

/**
 * Draw web shot lines with glow effect.
 */
export function drawWebShot(
  ctx: CanvasRenderingContext2D,
  web: WebShot,
  width: number,
  height: number,
  constants: SharedConstants
): void {
  const { WEB_LINE_THICKNESS, WEB_GLOW_THICKNESS } = constants;

  const startX = web.start.x * width;
  const startY = web.start.y * height;
  const alpha = web.alpha / 255;

  web.lines.forEach((line) => {
    const endX = line.end.x * width;
    const endY = line.end.y * height;

    // Glow layer
    ctx.strokeStyle = `rgba(150, 150, 255, ${alpha * 0.5})`;
    ctx.lineWidth = WEB_GLOW_THICKNESS;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();

    // Core white line
    ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
    ctx.lineWidth = WEB_LINE_THICKNESS;
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();
  });
}

/**
 * Draw THWIP! text effect.
 */
export function drawThwip(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  age: number, // 0-1, how old the effect is
  width: number,
  height: number
): void {
  const pixelX = x * width;
  const pixelY = y * height;

  // Fade out as age increases
  const alpha = Math.max(0, 1 - age);
  const scale = 1 + age * 0.5; // Grow slightly

  ctx.save();
  ctx.translate(pixelX, pixelY);
  ctx.scale(scale, scale);

  // Text shadow
  ctx.fillStyle = `rgba(0, 0, 0, ${alpha * 0.5})`;
  ctx.font = 'bold 48px Comic Sans MS, Impact, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('THWIP!', 3, 3);

  // Main text
  ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
  ctx.fillText('THWIP!', 0, 0);

  ctx.restore();
}

/**
 * Clear the canvas.
 */
export function clearCanvas(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
}
