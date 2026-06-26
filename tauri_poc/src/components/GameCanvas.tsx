/**
 * GameCanvas - Main game display component
 * Renders video frame + canvas overlay with all game graphics
 */

import { useEffect, useRef, useCallback } from 'react';
import { listen, UnlistenFn } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';
import { useGameEngine } from '../lib/gameEngine';
import * as Draw from '../lib/drawUtils';
import * as C from '../lib/constants';
import { DetectionEvent, FrameEvent, StatsEvent } from '../lib/types';

interface GameCanvasProps {
  onStatsUpdate?: (fps: number, detectionMs: number) => void;
  onStateChange?: (state: string) => void;
}

export default function GameCanvas({ onStatsUpdate, onStateChange }: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<string | null>(null);
  const animationRef = useRef<number | null>(null);
  
  // Latest detection data
  const detectionRef = useRef<DetectionEvent | null>(null);
  
  // Game engine
  const { update: updateGame, reset: resetGame } = useGameEngine();
  
  // Animation loop - renders at 60fps
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    const { width, height } = canvas;
    const detection = detectionRef.current;
    
    // Clear canvas
    Draw.clearCanvas(ctx, width, height);
    
    // Draw video frame as background if available
    if (frameRef.current) {
      const img = new Image();
      img.src = `data:image/jpeg;base64,${frameRef.current}`;
      // Note: For better performance, we'd use createImageBitmap or a <video> element
      // This is simplified for POC
      if (img.complete) {
        ctx.drawImage(img, 0, 0, width, height);
      }
    }
    
    // Extract data from detection
    let triggerFired = false;
    let wristPos: { x: number; y: number } | null = null;
    let elbowPos: { x: number; y: number } | null = null;
    let landmarks: [number, number, number][] | null = null;
    let gestureDetected = false;
    let state = 'LOOKING';
    
    if (detection) {
      triggerFired = detection.trigger_fired;
      gestureDetected = detection.gesture?.is_spiderman ?? false;
      state = detection.state;
      
      if (detection.hand?.landmarks) {
        landmarks = detection.hand.landmarks;
        // Wrist is landmark 0
        const wrist = landmarks[0];
        if (wrist) {
          wristPos = { x: wrist[0], y: wrist[1] };
        }
      }
      
      // Get elbow from pose
      const handedness = detection.hand?.handedness ?? 'Right';
      if (handedness === 'Right' && detection.pose?.right_elbow) {
        const elbow = detection.pose.right_elbow;
        elbowPos = { x: elbow[0], y: elbow[1] };
      } else if (handedness === 'Left' && detection.pose?.left_elbow) {
        const elbow = detection.pose.left_elbow;
        elbowPos = { x: elbow[0], y: elbow[1] };
      }
    }
    
    // Update game engine
    const gameState = updateGame(triggerFired, wristPos, elbowPos);
    
    // Draw symbiote balls
    for (const ball of gameState.balls) {
      Draw.drawSymbiote(ctx, ball, width, height);
    }
    
    // Draw hand landmarks (Spider-Man glove style)
    if (landmarks) {
      Draw.drawSpidermanHand(ctx, landmarks, width, height);
    }
    
    // Draw web shots
    for (const web of gameState.webShots) {
      Draw.drawWebShot(ctx, web, width, height);
    }
    
    // Draw THWIP effect
    if (gameState.thwip) {
      const age = Date.now() - gameState.thwip.createdAt;
      Draw.drawThwip(ctx, gameState.thwip.x, gameState.thwip.y, age, width, height);
    }
    
    // Draw state indicator
    Draw.drawStateIndicator(ctx, state, gestureDetected, width);
    
    // Draw score
    Draw.drawScore(ctx, gameState.score, height);
    
    // Continue animation loop
    animationRef.current = requestAnimationFrame(animate);
  }, [updateGame]);
  
  // Setup Tauri event listeners
  useEffect(() => {
    const unlisteners: UnlistenFn[] = [];
    
    // Listen for frame events
    listen<FrameEvent>('frame', (event) => {
      frameRef.current = event.payload.data;
    }).then(unlisten => unlisteners.push(unlisten));
    
    // Listen for detection events
    listen<DetectionEvent>('detection', (event) => {
      detectionRef.current = event.payload;
      onStateChange?.(event.payload.state);
    }).then(unlisten => unlisteners.push(unlisten));
    
    // Listen for stats events
    listen<StatsEvent>('stats', (event) => {
      onStatsUpdate?.(event.payload.fps, 0);
    }).then(unlisten => unlisteners.push(unlisten));
    
    // Start the Python detector
    invoke('start_detector').catch(console.error);
    
    // Reset game
    resetGame();
    
    // Cleanup
    return () => {
      unlisteners.forEach(unlisten => unlisten());
      invoke('stop_detector').catch(console.error);
    };
  }, [onStatsUpdate, onStateChange, resetGame]);
  
  // Start animation loop
  useEffect(() => {
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [animate]);
  
  return (
    <div 
      className="relative mx-auto border-4 border-spidey-red rounded-lg overflow-hidden shadow-2xl game-container"
      style={{ width: C.FRAME_WIDTH, height: C.FRAME_HEIGHT }}
    >
      {/* Canvas for all rendering (video + graphics) */}
      <canvas
        ref={canvasRef}
        width={C.FRAME_WIDTH}
        height={C.FRAME_HEIGHT}
        className="absolute top-0 left-0 w-full h-full bg-gray-900"
      />
      
      {/* Mode indicator */}
      <div className="absolute top-4 right-4 px-3 py-1 bg-green-600/70 rounded text-sm text-white font-bold">
        🕷️ TAURI MODE
      </div>
    </div>
  );
}
