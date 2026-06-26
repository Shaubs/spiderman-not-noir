/**
 * Game Engine - Handles all game logic in React
 * Matches Python implementation exactly
 * 
 * Manages:
 * - Symbiote ball spawning, movement, and wobble animation
 * - Web shooting with 3-line spread
 * - Collision detection (line-circle intersection)
 * - Grayscale infection system (permanent zones)
 * - Score tracking
 */

import { useRef, useCallback } from 'react';
import { SymbioteBall, WebShot, GameScore, GameState, InfectedZone } from './types';
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
  const infectedZonesRef = useRef<InfectedZone[]>([]);
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
   * Spawn a single symbiote ball from a specific edge
   */
  const spawnSingleBall = useCallback((edge: string) => {
    if (ballsRef.current.length >= C.SYMBIOTE_MAX_COUNT) return;
    
    const now = Date.now();
    
    let startX: number, startY: number;
    switch (edge) {
      case 'top':
        startX = 0.08 + Math.random() * 0.84;
        startY = 0;
        break;
      case 'left':
        startX = 0;
        startY = (50 + Math.random() * (C.FRAME_HEIGHT / 2 - 50)) / C.FRAME_HEIGHT;
        break;
      case 'right':
        startX = 1;
        startY = (50 + Math.random() * (C.FRAME_HEIGHT / 2 - 50)) / C.FRAME_HEIGHT;
        break;
      case 'top_left':
        startX = Math.random() * (50 / C.FRAME_WIDTH);
        startY = Math.random() * (50 / C.FRAME_HEIGHT);
        break;
      default: // top_right
        startX = 1 - Math.random() * (50 / C.FRAME_WIDTH);
        startY = Math.random() * (50 / C.FRAME_HEIGHT);
        break;
    }
    
    // Target: random position anywhere on screen
    const marginX = 0.1;
    const marginY = 0.1;
    const targetX = marginX + Math.random() * (1 - 2 * marginX);
    const targetY = marginY + Math.random() * (1 - 2 * marginY);
    
    const ball: SymbioteBall = {
      id: `ball_${now}_${Math.random().toString(36).substr(2, 9)}`,
      startX,
      startY,
      targetX,
      targetY,
      createdAt: now,
      travelTime: C.SYMBIOTE_TRAVEL_TIME,
      startSize: C.SYMBIOTE_START_SIZE,
      endSize: C.SYMBIOTE_END_SIZE,
      wobblePhase: Math.random() * Math.PI * 2,
      isDestroyed: false,
    };
    
    ballsRef.current.push(ball);
  }, []);

  /**
   * Spawn multiple symbiote balls (3-4 at a time)
   * Each spawns from a different edge for variety
   */
  const spawnBalls = useCallback(() => {
    // Spawn 3-4 balls at once
    const numToSpawn = 3 + Math.floor(Math.random() * 2); // 3 or 4
    const edges = ['top', 'left', 'right', 'top_left', 'top_right'];
    
    for (let i = 0; i < numToSpawn; i++) {
      if (ballsRef.current.length >= C.SYMBIOTE_MAX_COUNT) break;
      
      // Pick a random edge for each ball
      const edge = edges[Math.floor(Math.random() * edges.length)];
      spawnSingleBall(edge);
    }
    
    lastSpawnRef.current = Date.now();
  }, [spawnSingleBall]);
  
  /**
   * Fire web shot from wrist position using elbow→wrist direction
   * Matches Python web_renderer.py shoot_web exactly
   * 
   * Creates 3 web lines: center, left (-15°), right (+15°)
   * Web extends to edge of screen (max_extend = max(width, height) * 2)
   */
  const fireWeb = useCallback((wristX: number, wristY: number, elbowX?: number, elbowY?: number) => {
    const now = Date.now();
    console.log('🕸️ fireWeb called:', { wristX, wristY, elbowX, elbowY });
    
    // Calculate direction from elbow to wrist (like Python)
    let dx: number, dy: number;
    if (elbowX !== undefined && elbowY !== undefined) {
      dx = wristX - elbowX;
      dy = wristY - elbowY;
    } else {
      // Fallback: shoot upward/forward
      dx = 0;
      dy = -0.5;
    }
    
    // Normalize direction vector
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len > 0) {
      dx /= len;
      dy /= len;
    }
    
    // Calculate angles (matches Python depth_config.py web_spread_angle=15.0)
    const centerAngle = Math.atan2(dy, dx);
    const spreadRad = (C.WEB_SPREAD_ANGLE * Math.PI) / 180;
    const leftAngle = centerAngle - spreadRad;
    const rightAngle = centerAngle + spreadRad;
    
    // Web extends VERY far - across entire screen and beyond
    // Use 5.0 to ensure web reaches any edge from any position
    const maxExtend = 5.0;
    
    // Create 3 web lines: left, center, right (matches Python)
    const angles = [leftAngle, centerAngle, rightAngle];
    
    for (let i = 0; i < angles.length; i++) {
      const angle = angles[i];
      const endX = wristX + Math.cos(angle) * maxExtend;
      const endY = wristY + Math.sin(angle) * maxExtend;
      
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
  }, []);
  
  /**
   * Check collisions between webs and balls
   * Uses line-circle intersection (matches Python symbiote.py check_web_collision)
   */
  const checkCollisions = useCallback(() => {
    const now = Date.now();
    
    for (const web of webShotsRef.current) {
      // Calculate web progress (how far it has traveled)
      const webAge = now - web.createdAt;
      const webProgress = Math.min(1, webAge / C.WEB_DURATION);
      
      // Current web endpoint (not full length yet)
      const currentEndX = web.startX + (web.endX - web.startX) * webProgress;
      const currentEndY = web.startY + (web.endY - web.startY) * webProgress;
      
      for (const ball of ballsRef.current) {
        if (ball.isDestroyed) continue;
        
        // Calculate ball's current position (same formula as render)
        const progress = Math.min(1, (now - ball.createdAt) / ball.travelTime);
        
        // Base position
        const baseX = ball.startX + (ball.targetX - ball.startX) * progress;
        const baseY = ball.startY + (ball.targetY - ball.startY) * progress;
        
        // Add wobble (must match render calculation exactly)
        let ballX = baseX;
        let ballY = baseY;
        
        if (C.WOBBLE_ENABLED && progress < 1) {
          const dx = ball.targetX - ball.startX;
          const dy = ball.targetY - ball.startY;
          const len = Math.sqrt(dx * dx + dy * dy);
          
          if (len > 0) {
            const perpX = -dy / len;
            const perpY = dx / len;
            
            // Same formula as render wobble
            const timeElapsed = (now - ball.createdAt) / 1000;
            const phase = timeElapsed * C.WOBBLE_FREQUENCY * 2 * Math.PI + ball.wobblePhase;
            let amplitude = C.WOBBLE_AMPLITUDE;
            if (C.WOBBLE_DECAY) {
              amplitude *= (1 - progress);
            }
            const wobbleMagnitude = Math.sin(phase) * amplitude;
            
            ballX += (perpX * wobbleMagnitude) / C.FRAME_WIDTH;
            ballY += (perpY * wobbleMagnitude) / C.FRAME_HEIGHT;
          }
        }
        
        // Ball radius for collision (matches Python: current_size * hit_radius_multiplier)
        const currentSize = C.SYMBIOTE_START_SIZE + 
          (C.SYMBIOTE_END_SIZE - C.SYMBIOTE_START_SIZE) * progress;
        // Convert to normalized coordinates for collision
        const ballRadius = (currentSize * C.HIT_RADIUS_MULTIPLIER) / C.FRAME_WIDTH;
        
        // Check line-circle intersection
        if (lineCircleIntersection(
          web.startX, web.startY,
          currentEndX, currentEndY,
          ballX, ballY, ballRadius
        )) {
          // Hit! Destroy ball
          ball.isDestroyed = true;
          scoreRef.current.ballsDestroyed++;
          scoreRef.current.combo++;
          
          // THWIP effect at BALL position (collision point)
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
    
    // Spawn balls periodically (3-4 at a time)
    if (now - lastSpawnRef.current > C.SYMBIOTE_SPAWN_INTERVAL) {
      spawnBalls();
    }
    
    // Fire web if trigger was fired (from Python state machine)
    if (triggerFired && wristPos) {
      const elbow = elbowPos || lastElbowRef.current;
      fireWeb(wristPos.x, wristPos.y, elbow?.x, elbow?.y);
    }
    
    // Check collisions
    checkCollisions();
    
    // Check for balls that hit player (reached target) - creates infected zone
    for (const ball of ballsRef.current) {
      if (ball.isDestroyed) continue;
      
      const progress = (now - ball.createdAt) / ball.travelTime;
      if (progress >= 1) {
        ball.isDestroyed = true;
        scoreRef.current.hitsTaken++;
        scoreRef.current.combo = 0;
        
        // Create infected zone at ball's target position
        // Radius = end_size * grayscale_radius_multiplier (like symbiote_config.py)
        if (C.INFECTION_ENABLED) {
          const infectionRadius = (ball.endSize * C.INFECTION_RADIUS_MULTIPLIER) / C.FRAME_WIDTH;
          
          // Check if this area is already mostly infected (optimization)
          const isAlreadyInfected = infectedZonesRef.current.some(zone => {
            const dx = zone.x - ball.targetX;
            const dy = zone.y - ball.targetY;
            const dist = Math.sqrt(dx * dx + dy * dy);
            // If new zone center is inside existing zone, skip
            return dist < zone.radius * 0.8;
          });
          
          if (!isAlreadyInfected) {
            infectedZonesRef.current.push({
              id: `infection_${now}_${ball.id}`,
              x: ball.targetX,
              y: ball.targetY,
              radius: infectionRadius,
              createdAt: now,
            });
          }
        }
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
    // Matches Python symbiote.py _wobble_offset and depth_config.py calculate_wobble EXACTLY
    const ballsWithPositions = ballsRef.current.map(ball => {
      const progress = Math.min(1, (now - ball.createdAt) / ball.travelTime);
      const baseX = ball.startX + (ball.targetX - ball.startX) * progress;
      const baseY = ball.startY + (ball.targetY - ball.startY) * progress;
      
      // Calculate wobble perpendicular to travel direction
      let wobbleX = 0;
      let wobbleY = 0;
      
      if (C.WOBBLE_ENABLED && progress < 1) {
        // Travel direction vector
        const dx = ball.targetX - ball.startX;
        const dy = ball.targetY - ball.startY;
        const len = Math.sqrt(dx * dx + dy * dy);
        
        if (len > 0) {
          // Perpendicular unit vector (rotate 90 degrees)
          const perpX = -dy / len;
          const perpY = dx / len;
          
          // Python formula: sin(time_elapsed * frequency * 2π + unique_phase) * amplitude
          // time_elapsed = ball.age in Python = (now - createdAt) / 1000
          const timeElapsed = (now - ball.createdAt) / 1000;
          const phase = timeElapsed * C.WOBBLE_FREQUENCY * 2 * Math.PI + ball.wobblePhase;
          
          // Amplitude in pixels, decays with progress if enabled
          let amplitude = C.WOBBLE_AMPLITUDE;
          if (C.WOBBLE_DECAY) {
            amplitude *= (1 - progress);
          }
          
          // Calculate wobble offset
          const wobbleMagnitude = Math.sin(phase) * amplitude;
          
          // Convert to normalized coordinates
          wobbleX = (perpX * wobbleMagnitude) / C.FRAME_WIDTH;
          wobbleY = (perpY * wobbleMagnitude) / C.FRAME_HEIGHT;
        }
      }
      
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
      webShots: webShotsRef.current.map(w => ({ ...w })),
      score: { ...scoreRef.current },
      triggerState: 'LOOKING', // State machine is in Python now
      thwip: thwipRef.current ? { ...thwipRef.current } : null,
      infectedZones: infectedZonesRef.current.map(z => ({ ...z })),
    };
  }, [spawnBalls, fireWeb, checkCollisions]);
  
  /**
   * Reset game
   */
  const reset = useCallback(() => {
    ballsRef.current = [];
    webShotsRef.current = [];
    infectedZonesRef.current = [];
    scoreRef.current = { websShot: 0, ballsDestroyed: 0, hitsTaken: 0, combo: 0 };
    thwipRef.current = null;
    lastSpawnRef.current = 0;
  }, []);
  
  return { update, reset, fireWeb };
}

/**
 * Check if line segment intersects circle
 * Matches Python symbiote.py _line_circle_intersection
 */
function lineCircleIntersection(
  x1: number, y1: number,
  x2: number, y2: number,
  cx: number, cy: number,
  radius: number
): boolean {
  // Vector from start to end
  const dx = x2 - x1;
  const dy = y2 - y1;
  
  // Vector from start to circle center
  const fx = x1 - cx;
  const fy = y1 - cy;
  
  const a = dx * dx + dy * dy;
  const b = 2 * (fx * dx + fy * dy);
  const c = fx * fx + fy * fy - radius * radius;
  
  if (a === 0) {
    // Line is a point
    return Math.sqrt(fx * fx + fy * fy) <= radius;
  }
  
  const discriminant = b * b - 4 * a * c;
  if (discriminant < 0) {
    return false;
  }
  
  const sqrtD = Math.sqrt(discriminant);
  const t1 = (-b - sqrtD) / (2 * a);
  const t2 = (-b + sqrtD) / (2 * a);
  
  // Check if intersection is within line segment (t in [0, 1])
  return (t1 >= 0 && t1 <= 1) || (t2 >= 0 && t2 <= 1) || (t1 < 0 && t2 > 1);
}
