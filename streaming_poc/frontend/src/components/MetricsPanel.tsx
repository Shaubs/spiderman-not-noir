import { useMemo } from 'react';
import { GameState } from '../lib/types';

interface MetricsPanelProps {
  gameState: GameState | null;
}

export default function MetricsPanel({ gameState }: MetricsPanelProps) {
  // Calculate metrics
  const metrics = useMemo(() => {
    if (!gameState) {
      return {
        frameId: '--',
        latency: '--',
        detectionTime: '--',
        avgDetectionTime: '--',
        state: '--',
      };
    }

    // Latency: difference between server timestamp and client receive time
    const clientTime = Date.now();
    const latency = Math.round(clientTime - gameState.server_timestamp);

    return {
      frameId: gameState.frame_id,
      latency: latency > 0 ? latency : 0, // Clamp negative (clock drift)
      detectionTime: gameState.detection_time_ms.toFixed(1),
      avgDetectionTime: gameState.avg_detection_time_ms.toFixed(1),
      state: gameState.state,
    };
  }, [gameState]);

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 mb-6 border border-gray-700">
      <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
        📊 Performance Metrics
        <span className="text-xs text-gray-400 font-normal">
          (for latency & frame sync testing)
        </span>
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Frame ID */}
        <MetricCard
          label="Frame ID"
          value={metrics.frameId}
          unit=""
          color="text-blue-400"
        />

        {/* Latency */}
        <MetricCard
          label="Latency"
          value={metrics.latency}
          unit="ms"
          color={getLatencyColor(Number(metrics.latency))}
          tooltip="Time from server to client"
        />

        {/* Detection Time */}
        <MetricCard
          label="Detection"
          value={metrics.detectionTime}
          unit="ms"
          color="text-purple-400"
          tooltip="MediaPipe detection time"
        />

        {/* Avg Detection */}
        <MetricCard
          label="Avg Detection"
          value={metrics.avgDetectionTime}
          unit="ms"
          color="text-purple-300"
          tooltip="Rolling average"
        />

        {/* Game State */}
        <MetricCard
          label="State"
          value={metrics.state}
          unit=""
          color={getStateColor(metrics.state)}
        />
      </div>

      {/* Game info */}
      {gameState && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex flex-wrap gap-6 text-sm">
            <span className="text-gray-400">
              Symbiotes: <span className="text-white font-mono">{gameState.symbiotes.length}</span>
            </span>
            <span className="text-gray-400">
              Hand: <span className={gameState.hand?.detected ? 'text-green-400' : 'text-red-400'}>
                {gameState.hand?.detected ? '✓ Detected' : '✗ Not detected'}
              </span>
            </span>
            <span className="text-gray-400">
              Gesture: <span className={gameState.gesture_detected ? 'text-yellow-400 font-bold' : 'text-gray-500'}>
                {gameState.gesture_name || 'None'}
                {gameState.gesture_detected && ' 🕷️'}
              </span>
            </span>
            <span className="text-gray-400">
              Web Shots: <span className="text-white font-mono">{gameState.web_shots.length}</span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper component for individual metrics
interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  color: string;
  tooltip?: string;
}

function MetricCard({ label, value, unit, color, tooltip }: MetricCardProps) {
  return (
    <div 
      className="bg-gray-900/50 rounded-lg p-3 text-center"
      title={tooltip}
    >
      <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className={`text-2xl font-mono font-bold ${color}`}>
        {value}
        {unit && <span className="text-sm text-gray-500 ml-1">{unit}</span>}
      </div>
    </div>
  );
}

// Color helpers based on values
function getLatencyColor(latency: number): string {
  if (isNaN(latency) || latency === 0) return 'text-gray-400';
  if (latency < 50) return 'text-green-400';
  if (latency < 100) return 'text-yellow-400';
  if (latency < 200) return 'text-orange-400';
  return 'text-red-400';
}

function getStateColor(state: string): string {
  switch (state) {
    case 'LOOKING':
      return 'text-gray-400';
    case 'DETECTED':
      return 'text-yellow-400';
    case 'TRIGGERED':
      return 'text-green-400';
    case 'COOLDOWN':
      return 'text-blue-400';
    default:
      return 'text-gray-400';
  }
}
