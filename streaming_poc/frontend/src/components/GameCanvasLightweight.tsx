/**
 * Lightweight GameCanvas - Uses lightweight WebSocket + React game engine
 * 
 * This version moves game logic (balls, webs, collisions) to React
 * for smoother 60fps animation, independent of MediaPipe detection rate.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { LightweightState, SharedConstants } from '../lib/types';
import { clearCanvas } from '../lib/draw_utils';
import { useGameEngine } from '../lib/gameEngine';
import constants from '../lib/constants.json';

interface GameCanvasLightweightProps {
  onStateUpdate: (state: LightweightState) => void;
  onConnectionChange: (connected: boolean) => void;
  overlayEnabled: boolean;
}

export default function GameCanvasLightweight({ 
  onStateUpdate, 
  onConnectionChange, 
  overlayEnabled 
}: GameCanvasLightweightProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  // Use refs to avoid stale closures in WebSocket callbacks
  const overlayEnabledRef = useRef(overlayEnabled);
  const onStateUpdateRef = useRef(onStateUpdate);
  const onConnectionChangeRef = useRef(onConnectionChange);
  
  // Latest detection data from WebSocket
  const latestStateRef = useRef<LightweightState | null>(null);
  
  // Track if we need to render
  const [, setRenderTrigger] = useState(0);
  
  // Type assertion for constants
  const CONSTANTS = constants as unknown as SharedConstants;
  
  // Initialize game engine
  const { update: updateGame, reset: resetGame } = useGameEngine(
    CONSTANTS.FRAME_WIDTH,
    CONSTANTS.FRAME_HEIGHT
  );
  
  // Keep refs up to date
  useEffect(() => {
    overlayEnabledRef.current = overlayEnabled;
  }, [overlayEnabled]);
  
  useEffect(() => {
    onStateUpdateRef.current = onStateUpdate;
  }, [onStateUpdate]);
  
  useEffect(() => {
    onConnectionChangeRef.current = onConnectionChange;
  }, [onConnectionChange]);

  // Draw state indicator on canvas
  const drawStateIndicator = (
    ctx: CanvasRenderingContext2D, 
    state: string, 
    gestureDetected: boolean,
    width: number
  ) => {
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
  };

  // Draw Spider-Man style hand from [x,y,z][] array format
  const drawSpidermanHandFromArray = (
    ctx: CanvasRenderingContext2D,
    landmarks: [number, number, number][],
    width: number,
    height: number,
    constants: SharedConstants
  ) => {
    if (landmarks.length < 21) return;
    
    const { HAND_CONNECTIONS, PALM_POLYGON, COLORS, HAND_CONNECTOR_THICKNESS, HAND_LANDMARK_RADIUS } = constants;
    
    // Draw connections (red lines between landmarks)
    ctx.strokeStyle = COLORS.SPIDEY_RED || '#B71C1C';
    ctx.lineWidth = HAND_CONNECTOR_THICKNESS;
    ctx.lineCap = 'round';
    
    for (const [start, end] of HAND_CONNECTIONS) {
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
    if (PALM_POLYGON.length >= 3) {
      ctx.fillStyle = 'rgba(183, 28, 28, 0.3)';
      ctx.beginPath();
      const firstIdx = PALM_POLYGON[0];
      const firstLm = landmarks[firstIdx];
      if (firstLm) {
        ctx.moveTo(firstLm[0] * width, firstLm[1] * height);
        for (let i = 1; i < PALM_POLYGON.length; i++) {
          const lm = landmarks[PALM_POLYGON[i]];
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
      ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.beginPath();
      ctx.arc(x, y, HAND_LANDMARK_RADIUS + 2, 0, Math.PI * 2);
      ctx.fill();
      
      // Core
      ctx.fillStyle = COLORS.SPIDEY_BLUE || '#1565C0';
      ctx.beginPath();
      ctx.arc(x, y, HAND_LANDMARK_RADIUS, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  // Draw symbiote ball (local function for game engine balls)
  const drawSymbiote = (
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    size: number,
    isDestroyed: boolean,
    width: number,
    height: number
  ) => {
    const pixelX = x * width;
    const pixelY = y * height;
    
    if (isDestroyed) {
      // Explosion effect
      ctx.fillStyle = 'rgba(75, 0, 130, 0.5)';
      ctx.beginPath();
      ctx.arc(pixelX, pixelY, size * 1.5, 0, Math.PI * 2);
      ctx.fill();
      return;
    }
    
    // Glow
    const gradient = ctx.createRadialGradient(
      pixelX, pixelY, 0,
      pixelX, pixelY, size + 10
    );
    gradient.addColorStop(0, 'rgba(75, 0, 130, 0.8)');
    gradient.addColorStop(0.5, 'rgba(75, 0, 130, 0.4)');
    gradient.addColorStop(1, 'rgba(75, 0, 130, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(pixelX, pixelY, size + 10, 0, Math.PI * 2);
    ctx.fill();
    
    // Core
    ctx.fillStyle = '#4B0082';
    ctx.beginPath();
    ctx.arc(pixelX, pixelY, size, 0, Math.PI * 2);
    ctx.fill();
  };

  // Draw web shot
  const drawWebShot = (
    ctx: CanvasRenderingContext2D,
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    alpha: number,
    width: number,
    height: number
  ) => {
    const x1 = startX * width;
    const y1 = startY * height;
    const x2 = endX * width;
    const y2 = endY * height;
    
    // Glow
    ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.3 / 255})`;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    
    // Main line
    ctx.strokeStyle = `rgba(255, 255, 255, ${alpha / 255})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  };

  // Draw THWIP text
  const drawThwip = (
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    age: number,
    width: number,
    height: number
  ) => {
    const pixelX = x * width;
    const pixelY = y * height;
    const alpha = Math.max(0, 1 - age / 500);
    const scale = 1 + age * 0.002;
    
    ctx.save();
    ctx.translate(pixelX, pixelY - 20);
    ctx.scale(scale, scale);
    ctx.font = 'bold 24px Comic Sans MS, cursive';
    ctx.fillStyle = `rgba(255, 255, 0, ${alpha})`;
    ctx.strokeStyle = `rgba(0, 0, 0, ${alpha})`;
    ctx.lineWidth = 2;
    ctx.textAlign = 'center';
    ctx.strokeText('THWIP!', 0, 0);
    ctx.fillText('THWIP!', 0, 0);
    ctx.restore();
  };

  // Animation loop - renders at 60fps
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      animationFrameRef.current = requestAnimationFrame(animate);
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      animationFrameRef.current = requestAnimationFrame(animate);
      return;
    }

    const { width, height } = canvas;
    const state = latestStateRef.current;

    // Clear previous frame
    clearCanvas(ctx, width, height);

    if (!overlayEnabledRef.current) {
      animationFrameRef.current = requestAnimationFrame(animate);
      return;
    }

    // Extract gesture info from state (new lightweight format)
    let gestureDetected = false;
    let wristPos: { x: number; y: number } | null = null;
    let elbowPos: { x: number; y: number } | null = null;
    let handLandmarks: [number, number, number][] | null = null;

    if (state) {
      // Gesture detected from Python's gesture classifier
      gestureDetected = state.gesture?.detected ?? false;
      
      // Hand landmarks are now [x, y, z][] arrays
      if (state.hand?.landmarks && state.hand.landmarks.length > 0) {
        handLandmarks = state.hand.landmarks;
        // Wrist is landmark 0: [x, y, z]
        const wrist = state.hand.landmarks[0];
        if (wrist) {
          wristPos = { x: wrist[0], y: wrist[1] };
        }
      }
      
      // Get elbow from pose (now [x, y] arrays)
      const handedness = state.hand?.handedness ?? 'Right';
      if (handedness === 'Right' && state.pose?.right_elbow) {
        const elbow = state.pose.right_elbow;
        elbowPos = { x: elbow[0], y: elbow[1] };
      } else if (handedness === 'Left' && state.pose?.left_elbow) {
        const elbow = state.pose.left_elbow;
        elbowPos = { x: elbow[0], y: elbow[1] };
      }
    }

    // Update game engine
    const gameState = updateGame(gestureDetected, wristPos, elbowPos);

    // Draw symbiote balls
    for (const ball of gameState.balls) {
      const currentX = 'currentX' in ball ? (ball as { currentX: number }).currentX : 0;
      const currentY = 'currentY' in ball ? (ball as { currentY: number }).currentY : 0;
      const currentSize = 'currentSize' in ball ? (ball as { currentSize: number }).currentSize : 20;
      drawSymbiote(ctx, currentX, currentY, currentSize, ball.isDestroyed, width, height);
    }

    // Draw hand landmarks (convert [x,y,z][] to Point3D[] for drawing)
    if (handLandmarks) {
      drawSpidermanHandFromArray(ctx, handLandmarks, width, height, CONSTANTS);
    }

    // Draw web shots
    for (const web of gameState.webShots) {
      drawWebShot(ctx, web.startX, web.startY, web.endX, web.endY, web.alpha, width, height);
    }

    // Draw THWIP
    if (gameState.thwip) {
      const age = Date.now() - gameState.thwip.createdAt;
      drawThwip(ctx, gameState.thwip.x, gameState.thwip.y, age, width, height);
    }

    // Draw state indicator
    drawStateIndicator(ctx, gameState.triggerState, gestureDetected, width);

    // Draw score
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(10, height - 60, 180, 50);
    ctx.fillStyle = '#FFD700';
    ctx.font = '14px monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`Webs: ${gameState.score.websShot}`, 20, height - 40);
    ctx.fillText(`Hits: ${gameState.score.ballsDestroyed}`, 20, height - 22);
    ctx.fillStyle = '#FF4444';
    ctx.fillText(`Taken: ${gameState.score.hitsTaken}`, 100, height - 40);
    ctx.fillStyle = '#00FF00';
    ctx.fillText(`Combo: ${gameState.score.combo}`, 100, height - 22);

    // Continue animation loop
    animationFrameRef.current = requestAnimationFrame(animate);
  }, [updateGame, CONSTANTS]);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/coordinates`;

    console.log('Connecting to Lightweight WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ Lightweight WebSocket connected');
      onConnectionChangeRef.current(true);
      resetGame();
    };

    ws.onmessage = (event) => {
      try {
        const state: LightweightState = JSON.parse(event.data);
        latestStateRef.current = state;
        onStateUpdateRef.current(state);
        // Trigger render update for metrics display
        setRenderTrigger(prev => prev + 1);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('❌ WebSocket disconnected, code:', event.code);
      onConnectionChangeRef.current(false);
      wsRef.current = null;
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('🔄 Reconnecting...');
        connectWebSocket();
      }, 2000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [resetGame]);

  // Start animation loop on mount
  useEffect(() => {
    animationFrameRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [animate]);

  // Connect WebSocket on mount
  useEffect(() => {
    connectWebSocket();

    return () => {
      console.log('🧹 Cleaning up WebSocket on unmount');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative mx-auto border-4 border-spidey-red rounded-lg overflow-hidden shadow-2xl"
         style={{ width: CONSTANTS.FRAME_WIDTH, height: CONSTANTS.FRAME_HEIGHT }}>
      {/* Layer 1: Video feed (raw camera, no graphics) */}
      <img
        src="/video/stream"
        alt="Camera feed"
        className="absolute top-0 left-0 w-full h-full object-cover"
        style={{ transform: 'scaleX(-1)' }}
      />

      {/* Layer 2: Canvas overlay (all graphics rendered by React at 60fps) */}
      <canvas
        ref={canvasRef}
        width={CONSTANTS.FRAME_WIDTH}
        height={CONSTANTS.FRAME_HEIGHT}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />

      {/* Mode indicator */}
      <div className="absolute top-4 right-4 px-2 py-1 bg-green-600/70 rounded text-xs text-white font-bold">
        ⚡ LIGHTWEIGHT MODE
      </div>
    </div>
  );
}
