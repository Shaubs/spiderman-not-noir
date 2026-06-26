import { useEffect, useRef, useCallback } from 'react';
import { GameState, SharedConstants } from '../lib/types';
import { drawSpidermanHand, drawSymbiote, drawWebShot, drawThwip, clearCanvas } from '../lib/draw_utils';
import constants from '../lib/constants.json';

interface GameCanvasProps {
  onStateUpdate: (state: GameState) => void;
  onConnectionChange: (connected: boolean) => void;
  overlayEnabled: boolean;
}

export default function GameCanvas({ 
  onStateUpdate, 
  onConnectionChange, 
  overlayEnabled 
}: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  
  // Use refs to avoid stale closures in WebSocket callbacks
  const overlayEnabledRef = useRef(overlayEnabled);
  const onStateUpdateRef = useRef(onStateUpdate);
  const onConnectionChangeRef = useRef(onConnectionChange);
  
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

  // Type assertion for constants
  const CONSTANTS = constants as unknown as SharedConstants;

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

  // Render overlay on canvas
  const renderOverlay = useCallback((state: GameState) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;

    // Clear previous frame
    clearCanvas(ctx, width, height);

    // Draw symbiotes
    state.symbiotes.forEach((sym) => {
      drawSymbiote(ctx, sym, width, height, CONSTANTS);
    });

    // Draw hand landmarks (Spider-Man glove style)
    if (state.hand?.detected && state.hand.landmarks) {
      drawSpidermanHand(ctx, state.hand.landmarks, width, height, CONSTANTS);
    }

    // Draw web shots
    state.web_shots.forEach((web) => {
      drawWebShot(ctx, web, width, height, CONSTANTS);
    });

    // Draw THWIP effect
    if (state.thwip) {
      const age = state.thwip.age ?? 0;
      drawThwip(ctx, state.thwip.x, state.thwip.y, age, width, height);
    }

    // Draw state indicator on canvas
    drawStateIndicator(ctx, state.state, state.gesture_detected ?? false, width);
  }, [CONSTANTS]);

  // WebSocket connection - using refs to avoid dependency changes
  const connectWebSocket = useCallback(() => {
    // Prevent multiple connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }
    
    // Use relative WebSocket URL for Vite proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/coordinates`;

    console.log('Connecting to WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ WebSocket connected and stable');
      onConnectionChangeRef.current(true);
    };

    ws.onmessage = (event) => {
      try {
        const state: GameState = JSON.parse(event.data);
        onStateUpdateRef.current(state);

        // Render overlay if enabled (using ref to get current value)
        if (overlayEnabledRef.current && canvasRef.current) {
          renderOverlay(state);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('❌ WebSocket disconnected, code:', event.code, 'reason:', event.reason);
      onConnectionChangeRef.current(false);
      
      // Clear the ref
      wsRef.current = null;
      
      // Reconnect after 2 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        console.log('🔄 Reconnecting...');
        connectWebSocket();
      }, 2000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [renderOverlay]); // Only depends on renderOverlay which is stable

  // Clear canvas when overlay is disabled
  useEffect(() => {
    if (!overlayEnabled && canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      if (ctx) {
        clearCanvas(ctx, canvasRef.current.width, canvasRef.current.height);
      }
    }
  }, [overlayEnabled]);

  // Connect on mount ONLY - no dependencies that would cause reconnection
  useEffect(() => {
    connectWebSocket();

    return () => {
      // Cleanup on unmount only
      console.log('🧹 Cleaning up WebSocket on unmount');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // Empty dependency array - only run on mount/unmount

  return (
    <div className="relative mx-auto border-4 border-spidey-red rounded-lg overflow-hidden shadow-2xl"
         style={{ width: CONSTANTS.FRAME_WIDTH, height: CONSTANTS.FRAME_HEIGHT }}>
      {/* Layer 1: Video feed (raw camera, no graphics) */}
      <img
        src="/video/stream"
        alt="Camera feed"
        className="absolute top-0 left-0 w-full h-full object-cover"
        style={{ transform: 'scaleX(-1)' }} // Mirror to match canvas flip
      />

      {/* Layer 2: Canvas overlay (all graphics rendered by React) */}
      <canvas
        ref={canvasRef}
        width={CONSTANTS.FRAME_WIDTH}
        height={CONSTANTS.FRAME_HEIGHT}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />

      {/* Overlay indicator */}
      <div className="absolute top-4 right-4 px-2 py-1 bg-black/50 rounded text-xs text-white">
        Overlay: {overlayEnabled ? 'ON' : 'OFF'}
      </div>
    </div>
  );
}
