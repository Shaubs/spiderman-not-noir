/**
 * Game Engine - Handles all game logic in React
 * 
 * Manages:
 * - Symbiote ball creation and animation
 * - Web shooting
 * - Collision detection
 * - Score tracking
 */

import { useRef, useCallback } from 'react';
import { SymbioteBall, WebShot, GameScore, GameState } from './types';
import * as C from './constants';

// Point type for internal use
interface Point2D {
  x: number;
  y: number;
}

/**
 * Game engine hook - manages all game state
 */
export function useGameEngine() {
  // Game state
  const ballsRef = useRef<SymbioteBall[]>([]);
  const webShotsRef = useRef<WebShot[]>([]);
  const scoreRef = useRef<GameScore>({
    websShot: 0,
    ballsDestroyed: 0,
    hitsTaken: 0,
    combo: 0,
  });
  const thwipRef = useRef<{ x: number; y: number; createdAt: number } | null>(null);
  
  // Spawn timing
  const lastSpawnRef = useRef<number>(0);
  
  // Last known wrist/elbow for web direction
  const lastWristRef = useRef<Point2D | null>(null);
  const lastElbowRef = useRef<Point2D | null>(null);
  
  /**
   * Spawn a new symbiote ball
   */
  const spawnBall = useCallback(() => {
    if (ballsRef.current.length >= C.SYMBIOTE_MAX_COUNT) return;
    
    const now = Date.now();
    
    // Random spawn position (edges of screen)
    const edge = Math.floor(Math.random() * 4);
    let startX: number, startY: number;
    
    switch (edge) {
      case 0: // Top
        startX = Math.random();
        startY = 0;
        break;
      case 1: // Right
        startX = 1;
        startY = Math.random();
        break;
      case 2: // Bottom
        startX = Math.random();
        startY = 1;
        break;
      default: // Left
        startX = 0;
        startY = Math.random();
        break;
    }
    
    // Target: center-ish of screen
    const targetX = 0.3 + Math.random() * 0.4;
    const targetY = 0.3 + Math.random() * 0.4;
    
    const ball: SymbioteBall = {
      id: `ball_${now}_${Math.random().toString(36).substr(2, 9)}`,
      startX,
      startY,
      targetX,
      targetY,
      createdAt: now,
      travelTime: C.SYMBIOTE_TRAVEL_TIME + Math.random() * 1000,
      startSize: 10,
      endSize: 50,
      wobblePhase: Math.random() * Math.PI * 2,
      isDestroyed: false,
    };
    
    ballsRef.current.push(ball);
    lastSpawnRef.current = now;
  }, []);
  
  /**
   * Fire web shot from wrist position
   */
  const fireWeb = useCallback((wristX: number, wristY: number, elbowX?: number, elbowY?: number) => {
    const now = Date.now();
    
    // Calculate direction
    let dx: number, dy: number;
    if (elbowX !== undefined && elbowY !== undefined) {
      dx = wristX - elbowX;
      dy = wristY - elbowY;
    } else {
      // Default: shoot upward-right
      dx = 0.3;
      dy = -0.5;
    }
    
    // Normalize
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len > 0) {
      dx /= len;
      dy /= len;
    }
    
    // Create web lines with spread
    const baseAngle = Math.atan2(dy, dx);
    const webLength = 0.4;
    
    for (let i = 0; i < C.WEB_LINE_COUNT; i++) {
      const angleOffset = (i - Math.floor(C.WEB_LINE_COUNT / 2)) * 
        (C.WEB_SPREAD_ANGLE * Math.PI / 180);
      const angle = baseAngle + angleOffset;
      
      const endX = wristX + Math.cos(angle) * webLength;
      const endY = wristY + Math.sin(angle) * webLength;
      
      const webShot: WebShot = {
        id: `web_${now}_${i}`,
        startX: wristX,
        startY: wristY,
        endX,
        endY,
        angle: angle * 180 / Math.PI,
        createdAt: now,
        alpha: 255,
      };
      
      webShotsRef.current.push(webShot);
    }
    
    scoreRef.current.websShot++;
    
    // Create THWIP effect at wrist
    thwipRef.current = {
      x: wristX,
      y: wristY,
      createdAt: now,
    };
  }, []);
  
  /**
   * Check collisions between webs and balls
   */
  const checkCollisions = useCallback(() => {
    const now = Date.now();
    
    for (const web of webShotsRef.current) {
      for (const ball of ballsRef.current) {
        if (ball.isDestroyed) continue;
        
        // Calculate ball's current position
        const progress = Math.min(1, (now - ball.createdAt) / ball.travelTime);
        const ballX = ball.startX + (ball.targetX - ball.startX) * progress;
        const ballY = ball.startY + (ball.targetY - ball.startY) * progress;
        
        // Point to line segment distance
        const dist = pointToSegmentDistance(
          ballX, ballY,
          web.startX, web.startY,
          web.endX, web.endY
        );
        
        const ballRadius = (ball.startSize + (ball.endSize - ball.startSize) * progress) / C.FRAME_WIDTH;
        
        if (dist < ballRadius + C.COLLISION_RADIUS) {
          // Hit!
          ball.isDestroyed = true;
          scoreRef.current.ballsDestroyed++;
          scoreRef.current.combo++;
          
          // THWIP at ball position
          thwipRef.current = {
            x: ballX,
            y: ballY,
            createdAt: now,
          };
        }
      }
    }
  }, []);
  
  /**
   * Update game state - called every frame
   */
  const update = useCallback((
    triggerFired: boolean,
    wristPos: Point2D | null,
    elbowPos: Point2D | null
  ): GameState => {
    const now = Date.now();
    
    // Store wrist/elbow for web direction
    if (wristPos) lastWristRef.current = wristPos;
    if (elbowPos) lastElbowRef.current = elbowPos;
    
    // Spawn balls periodically
    if (now - lastSpawnRef.current > C.SYMBIOTE_SPAWN_INTERVAL) {
      spawnBall();
    }
    
    // Fire web if trigger was fired (from Python state machine)
    if (triggerFired && wristPos) {
      const elbow = elbowPos || lastElbowRef.current;
      fireWeb(wristPos.x, wristPos.y, elbow?.x, elbow?.y);
    }
    
    // Check collisions
    checkCollisions();
    
    // Check for balls that hit player (reached target)
    for (const ball of ballsRef.current) {
      if (ball.isDestroyed) continue;
      
      const progress = (now - ball.createdAt) / ball.travelTime;
      if (progress >= 1) {
        ball.isDestroyed = true;
        scoreRef.current.hitsTaken++;
        scoreRef.current.combo = 0;
      }
    }
    
    // Cleanup expired balls
    ballsRef.current = ballsRef.current.filter(ball => {
      if (ball.isDestroyed) {
        const age = now - ball.createdAt;
        return age < ball.travelTime + 500; // Keep for a bit after destruction
      }
      return true;
    });
    
    // Cleanup expired web shots
    webShotsRef.current = webShotsRef.current.filter(web => {
      const age = now - web.createdAt;
      if (age >= C.WEB_DURATION) return false;
      web.alpha = 255 * (1 - age / C.WEB_DURATION);
      return true;
    });
    
    // Cleanup THWIP
    if (thwipRef.current) {
      const age = now - thwipRef.current.createdAt;
      if (age >= C.THWIP_DURATION) {
        thwipRef.current = null;
      }
    }
    
    // Calculate current ball positions with wobble
    const ballsWithPositions = ballsRef.current.map(ball => {
      const progress = Math.min(1, (now - ball.createdAt) / ball.travelTime);
      const baseX = ball.startX + (ball.targetX - ball.startX) * progress;
      const baseY = ball.startY + (ball.targetY - ball.startY) * progress;
      
      // Add wobble
      const wobbleAmplitude = 0.02;
      const wobbleFrequency = 3;
      const wobbleX = Math.sin(progress * Math.PI * wobbleFrequency + ball.wobblePhase) 
        * wobbleAmplitude * (1 - progress);
      const wobbleY = Math.cos(progress * Math.PI * wobbleFrequency + ball.wobblePhase) 
        * wobbleAmplitude * (1 - progress);
      
      return {
        ...ball,
        currentX: baseX + wobbleX,
        currentY: baseY + wobbleY,
        currentSize: ball.startSize + (ball.endSize - ball.startSize) * progress,
      };
    });
    
    return {
      balls: ballsWithPositions,
      webShots: webShotsRef.current.map(w => ({ ...w })),
      score: { ...scoreRef.current },
      triggerState: 'LOOKING', // State machine is in Python now
      thwip: thwipRef.current ? { ...thwipRef.current } : null,
    };
  }, [spawnBall, fireWeb, checkCollisions]);
  
  /**
   * Reset game
   */
  const reset = useCallback(() => {
    ballsRef.current = [];
    webShotsRef.current = [];
    scoreRef.current = { websShot: 0, ballsDestroyed: 0, hitsTaken: 0, combo: 0 };
    thwipRef.current = null;
    lastSpawnRef.current = 0;
  }, []);
  
  return { update, reset, fireWeb };
}

/**
 * Calculate distance from point to line segment
 */
function pointToSegmentDistance(
  px: number, py: number,
  x1: number, y1: number,
  x2: number, y2: number
): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  
  if (dx === 0 && dy === 0) {
    return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
  }
  
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)));
  
  const projX = x1 + t * dx;
  const projY = y1 + t * dy;
  
  return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2);
}
