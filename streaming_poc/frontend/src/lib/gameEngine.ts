/**
 * Game Engine - Handles all game logic in React
 * 
 * Manages:
 * - Symbiote ball creation and animation
 * - Web shooting
 * - Collision detection
 * - Score tracking
 * - State machine for gesture triggers
 */

import { useRef, useCallback } from 'react';

// Types
export interface Point2D {
  x: number;
  y: number;
}

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
}

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

export interface GameScore {
  websShot: number;
  ballsDestroyed: number;
  hitsTaken: number;
  combo: number;
}

export interface GameState {
  balls: SymbioteBall[];
  webShots: WebShot[];
  score: GameScore;
  triggerState: 'LOOKING' | 'DETECTED' | 'TRIGGERED' | 'COOLDOWN';
  thwip: { x: number; y: number; createdAt: number } | null;
}

// Configuration
const CONFIG = {
  // Symbiote balls
  spawnIntervalMs: 2000,
  maxBalls: 5,
  ballTravelTimeMs: 4000,
  ballStartSize: 10,
  ballEndSize: 50,
  wobbleAmplitude: 0.02,
  wobbleFrequency: 3,
  
  // Web shots
  webDurationMs: 500,
  webSpreadAngle: 10, // degrees
  webLineCount: 3,
  webLength: 0.4, // normalized
  
  // Trigger
  sustainedHoldMs: 400,
  cooldownMs: 300,
  
  // THWIP
  thwipDurationMs: 500,
  
  // Collision
  collisionRadius: 0.03, // normalized
};

/**
 * Game engine hook - manages all game state
 */
export function useGameEngine(frameWidth: number, _frameHeight: number) {
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
  
  // State machine
  const triggerStateRef = useRef<'LOOKING' | 'DETECTED' | 'TRIGGERED' | 'COOLDOWN'>('LOOKING');
  const detectedAtRef = useRef<number>(0);
  const lastTriggerRef = useRef<number>(0);
  
  // Spawn timing
  const lastSpawnRef = useRef<number>(0);
  
  // Last known wrist/elbow for web direction
  const lastWristRef = useRef<Point2D | null>(null);
  const lastElbowRef = useRef<Point2D | null>(null);
  
  /**
   * Spawn a new symbiote ball
   */
  const spawnBall = useCallback(() => {
    if (ballsRef.current.length >= CONFIG.maxBalls) return;
    
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
      travelTime: CONFIG.ballTravelTimeMs + Math.random() * 1000,
      startSize: CONFIG.ballStartSize,
      endSize: CONFIG.ballEndSize,
      wobblePhase: Math.random() * Math.PI * 2,
      isDestroyed: false,
    };
    
    ballsRef.current.push(ball);
    lastSpawnRef.current = now;
  }, []);
  
  /**
   * Fire web shot
   */
  const fireWeb = useCallback(() => {
    const wrist = lastWristRef.current;
    if (!wrist) return;
    
    const now = Date.now();
    const elbow = lastElbowRef.current;
    
    // Calculate direction
    let dx: number, dy: number;
    if (elbow) {
      dx = wrist.x - elbow.x;
      dy = wrist.y - elbow.y;
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
    
    for (let i = 0; i < CONFIG.webLineCount; i++) {
      const angleOffset = (i - Math.floor(CONFIG.webLineCount / 2)) * 
        (CONFIG.webSpreadAngle * Math.PI / 180);
      const angle = baseAngle + angleOffset;
      
      const endX = wrist.x + Math.cos(angle) * CONFIG.webLength;
      const endY = wrist.y + Math.sin(angle) * CONFIG.webLength;
      
      const webShot: WebShot = {
        id: `web_${now}_${i}`,
        startX: wrist.x,
        startY: wrist.y,
        endX,
        endY,
        angle: angle * 180 / Math.PI,
        createdAt: now,
        alpha: 255,
      };
      
      webShotsRef.current.push(webShot);
    }
    
    scoreRef.current.websShot++;
    
    // Create THWIP effect
    thwipRef.current = {
      x: wrist.x,
      y: wrist.y,
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
        
        const ballRadius = (ball.startSize + (ball.endSize - ball.startSize) * progress) / frameWidth;
        
        if (dist < ballRadius + CONFIG.collisionRadius) {
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
  }, [frameWidth]);
  
  /**
   * Update game state - called every frame
   */
  const update = useCallback((
    gestureDetected: boolean,
    wristPos: Point2D | null,
    elbowPos: Point2D | null
  ): GameState => {
    const now = Date.now();
    
    // Store wrist/elbow for web direction
    if (wristPos) lastWristRef.current = wristPos;
    if (elbowPos) lastElbowRef.current = elbowPos;
    
    // Spawn balls periodically
    if (now - lastSpawnRef.current > CONFIG.spawnIntervalMs) {
      spawnBall();
    }
    
    // Update state machine
    const prevState = triggerStateRef.current;
    
    if (triggerStateRef.current === 'COOLDOWN') {
      if (now - lastTriggerRef.current > CONFIG.cooldownMs) {
        triggerStateRef.current = 'LOOKING';
      }
    } else if (gestureDetected) {
      if (triggerStateRef.current === 'LOOKING') {
        triggerStateRef.current = 'DETECTED';
        detectedAtRef.current = now;
      } else if (triggerStateRef.current === 'DETECTED') {
        // Check sustained hold
        if (now - detectedAtRef.current > CONFIG.sustainedHoldMs) {
          triggerStateRef.current = 'TRIGGERED';
          lastTriggerRef.current = now;
          fireWeb();
        }
      }
    } else {
      if (triggerStateRef.current === 'DETECTED') {
        triggerStateRef.current = 'LOOKING';
      }
    }
    
    // Auto-transition from TRIGGERED to COOLDOWN
    if (triggerStateRef.current === 'TRIGGERED' && prevState === 'TRIGGERED') {
      triggerStateRef.current = 'COOLDOWN';
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
      if (age >= CONFIG.webDurationMs) return false;
      web.alpha = 255 * (1 - age / CONFIG.webDurationMs);
      return true;
    });
    
    // Cleanup THWIP
    if (thwipRef.current) {
      const age = now - thwipRef.current.createdAt;
      if (age >= CONFIG.thwipDurationMs) {
        thwipRef.current = null;
      }
    }
    
    // Calculate current ball positions with wobble
    const ballsWithPositions = ballsRef.current.map(ball => {
      const progress = Math.min(1, (now - ball.createdAt) / ball.travelTime);
      const baseX = ball.startX + (ball.targetX - ball.startX) * progress;
      const baseY = ball.startY + (ball.targetY - ball.startY) * progress;
      
      // Add wobble
      const wobbleX = Math.sin(progress * Math.PI * CONFIG.wobbleFrequency + ball.wobblePhase) 
        * CONFIG.wobbleAmplitude * (1 - progress);
      const wobbleY = Math.cos(progress * Math.PI * CONFIG.wobbleFrequency + ball.wobblePhase) 
        * CONFIG.wobbleAmplitude * (1 - progress);
      
      return {
        ...ball,
        currentX: baseX + wobbleX,
        currentY: baseY + wobbleY,
        currentSize: ball.startSize + (ball.endSize - ball.startSize) * progress,
        progress,
      };
    });
    
    return {
      balls: ballsWithPositions,
      webShots: webShotsRef.current,
      score: { ...scoreRef.current },
      triggerState: triggerStateRef.current,
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
    triggerStateRef.current = 'LOOKING';
  }, []);
  
  return { update, reset };
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
