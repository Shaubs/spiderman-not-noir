/**
 * GameCanvas - Main game display component
 * Renders video frame + canvas overlay with all game graphics
 * Uses MediaPipe JS for hand detection (no Python required)
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useGameEngine } from '../lib/gameEngine';
import { useHandDetection } from '../lib/useHandDetection';
import * as Draw from '../lib/drawUtils';
import * as C from '../lib/constants';

interface GameCanvasProps {
  onStatsUpdate?: (fps: number, detectionMs: number) => void;
  onStateChange?: (state: string) => void;
}

// Simple state machine for gesture triggering
interface GestureState {
  state: 'LOOKING' | 'DETECTED' | 'TRIGGERED';
  detectedAt: number | null;
  triggeredAt: number | null;
}

const HOLD_TIME_MS = 400; // Time to hold gesture before trigger
const COOLDOWN_MS = 500; // Cooldown after trigger

export default function GameCanvas({ onStatsUpdate, onStateChange }: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const animationRef = useRef<number | null>(null);
  const cameraReadyRef = useRef(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [detectorReady, setDetectorReady] = useState(false);
  
  // PERMANENT grayscale mask - never clears, only adds pixels
  // Like Python's _cached_grayscale_mask in symbiote.py
  const grayscaleMaskRef = useRef<Uint8Array | null>(null);
  const lastProcessedZoneCountRef = useRef(0);
  
  // Gesture state machine
  const gestureStateRef = useRef<GestureState>({
    state: 'LOOKING',
    detectedAt: null,
    triggeredAt: null,
  });
  
  // FPS tracking
  const fpsRef = useRef({ frames: 0, lastTime: performance.now(), fps: 0 });
  
  // Hand detection hook
  const { detect, isReady: handDetectorReady } = useHandDetection(videoRef, cameraReady);
  
  // Game engine
  const { update: updateGame, reset: resetGame } = useGameEngine();
  
  // Update detector ready state
  useEffect(() => {
    setDetectorReady(handDetectorReady);
  }, [handDetectorReady]);
  
  // Load THWIP image at startup
  useEffect(() => {
    Draw.loadThwipImage();
  }, []);
  
  // Initialize camera
  useEffect(() => {
    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: C.FRAME_WIDTH },
            height: { ideal: C.FRAME_HEIGHT },
            facingMode: 'user'
          }
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play();
            cameraReadyRef.current = true;
            setCameraReady(true);
          };
        }
      } catch (err) {
        console.error('Camera access error:', err);
      }
    };
    
    initCamera();
    
    // Cleanup
    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach(track => track.stop());
      }
    };
  }, []);
  
  // Animation loop - renders at 60fps
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (!canvas || !video) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    const { width, height } = canvas;
    
    // FPS tracking
    const now = performance.now();
    fpsRef.current.frames++;
    if (now - fpsRef.current.lastTime >= 1000) {
      fpsRef.current.fps = fpsRef.current.frames;
      fpsRef.current.frames = 0;
      fpsRef.current.lastTime = now;
      onStatsUpdate?.(fpsRef.current.fps, 0);
    }
    
    // Clear canvas
    Draw.clearCanvas(ctx, width, height);
    
    // Draw video frame (mirrored for selfie view)
    if (cameraReadyRef.current && video.readyState >= 2) {
      ctx.save();
      ctx.scale(-1, 1);
      ctx.drawImage(video, -width, 0, width, height);
      ctx.restore();
    }
    
    // Run hand detection
    const handResult = detect();
    
    // Update gesture state machine
    const gs = gestureStateRef.current;
    let triggerFired = false;
    
    if (handResult.isSpiderman) {
      if (gs.state === 'LOOKING') {
        gs.state = 'DETECTED';
        gs.detectedAt = now;
      } else if (gs.state === 'DETECTED' && gs.detectedAt) {
        // Check if held long enough
        if (now - gs.detectedAt >= HOLD_TIME_MS) {
          gs.state = 'TRIGGERED';
          gs.triggeredAt = now;
          triggerFired = true;
          console.log('🕷️ TRIGGER FIRED!');
        }
      } else if (gs.state === 'TRIGGERED' && gs.triggeredAt) {
        // Cooldown
        if (now - gs.triggeredAt >= COOLDOWN_MS) {
          gs.state = 'DETECTED';
          gs.detectedAt = now;
        }
      }
    } else {
      // Gesture lost
      if (gs.state !== 'TRIGGERED' || (gs.triggeredAt && now - gs.triggeredAt >= COOLDOWN_MS)) {
        gs.state = 'LOOKING';
        gs.detectedAt = null;
      }
    }
    
    onStateChange?.(gs.state);
    
    // Convert landmarks to the format expected by Draw functions
    let landmarks: [number, number, number][] | null = null;
    let wristPos: { x: number; y: number } | null = null;
    
    if (handResult.landmarks) {
      // Mirror x coordinate since video is mirrored
      landmarks = handResult.landmarks.map(lm => [
        1 - lm.x, // Mirror X
        lm.y,
        lm.z
      ] as [number, number, number]);
      
      wristPos = {
        x: 1 - handResult.landmarks[0].x, // Mirror X
        y: handResult.landmarks[0].y
      };
    }
    
    // Get elbow position (mirrored)
    let elbowPos: { x: number; y: number } | null = null;
    if (handResult.elbowPos) {
      elbowPos = {
        x: 1 - handResult.elbowPos.x, // Mirror X
        y: handResult.elbowPos.y
      };
    }
    
    // Update game engine
    const gameState = updateGame(triggerFired, wristPos, elbowPos);
    
    // Apply PERMANENT grayscale to infected zones
    // Uses cached mask that only adds pixels, never removes them
    if (gameState.infectedZones.length > 0) {
      Draw.applyPermanentGrayscale(
        ctx, 
        gameState.infectedZones, 
        width, 
        height,
        grayscaleMaskRef,
        lastProcessedZoneCountRef
      );
    } else if (grayscaleMaskRef.current) {
      // Even if no new zones, apply existing mask
      Draw.applyExistingGrayscaleMask(ctx, grayscaleMaskRef.current, width, height);
    }
    
    // Draw symbiote balls
    for (const ball of gameState.balls) {
      Draw.drawSymbiote(ctx, ball, width, height);
    }
    
    // Draw hand landmarks (Spider-Man glove style)
    if (landmarks) {
      Draw.drawSpidermanHand(ctx, landmarks, width, height);
    }
    
    // Draw web shots
    if (gameState.webShots.length > 0) {
      console.log('Drawing webs:', gameState.webShots.length, gameState.webShots[0]);
      // Visual debug - draw count on screen
      ctx.fillStyle = 'yellow';
      ctx.font = '30px Arial';
      ctx.fillText(`WEBS: ${gameState.webShots.length}`, 10, 100);
    }
    for (const web of gameState.webShots) {
      Draw.drawWebShot(ctx, web, width, height);
    }
    
    // DEBUG: Always draw a test line to verify canvas drawing works
    ctx.strokeStyle = 'lime';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(100, 100);
    ctx.lineTo(300, 300);
    ctx.stroke();
    
    // Draw THWIP effect
    if (gameState.thwip) {
      const age = Date.now() - gameState.thwip.createdAt;
      Draw.drawThwip(ctx, gameState.thwip.x, gameState.thwip.y, age, width, height);
    }
    
    // Draw state indicator
    Draw.drawStateIndicator(ctx, gs.state, handResult.isSpiderman, width);
    
    // Draw score
    Draw.drawScore(ctx, gameState.score, height);
    
    // Continue animation loop
    animationRef.current = requestAnimationFrame(animate);
  }, [detect, updateGame, onStatsUpdate, onStateChange]);
  
  // Start animation loop and reset game
  useEffect(() => {
    resetGame();
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [animate, resetGame]);
  
  return (
    <div 
      className="relative mx-auto border-4 border-spidey-red rounded-lg overflow-hidden shadow-2xl game-container"
      style={{ width: C.FRAME_WIDTH, height: C.FRAME_HEIGHT }}
    >
      {/* Hidden video element for camera capture */}
      <video
        ref={videoRef}
        playsInline
        muted
        className="hidden"
      />
      
      {/* Canvas for all rendering (video + graphics) */}
      <canvas
        ref={canvasRef}
        width={C.FRAME_WIDTH}
        height={C.FRAME_HEIGHT}
        className="absolute top-0 left-0 w-full h-full bg-gray-900"
      />
      
      {/* Status overlays */}
      {!cameraReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="text-white text-xl">📷 Initializing camera...</div>
        </div>
      )}
      
      {cameraReady && !detectorReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
          <div className="text-white text-xl">🤖 Loading hand detector...</div>
        </div>
      )}
      
      {/* Mode indicator */}
      <div className="absolute top-4 right-4 px-3 py-1 bg-green-600/70 rounded text-sm text-white font-bold">
        🕷️ TAURI + MediaPipe JS
      </div>
    </div>
  );
}
