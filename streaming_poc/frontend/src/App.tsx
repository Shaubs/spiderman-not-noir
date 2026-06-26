import { useState } from 'react'
import GameCanvas from './components/GameCanvas'
import GameCanvasLightweight from './components/GameCanvasLightweight'
import MetricsPanel from './components/MetricsPanel'
import Controls from './components/Controls'
import { GameState, LightweightState } from './lib/types'

// Toggle between modes - set to true to test lightweight mode
const USE_LIGHTWEIGHT_MODE = true;

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [lightweightState, setLightweightState] = useState<LightweightState | null>(null)
  const [overlayEnabled, setOverlayEnabled] = useState(true)
  const [isConnected, setIsConnected] = useState(false)
  const [useLightweight, setUseLightweight] = useState(USE_LIGHTWEIGHT_MODE)

  // Convert lightweight state to minimal GameState for MetricsPanel
  const metricsState = useLightweight && lightweightState ? {
    frame_id: lightweightState.frame_id,
    frame_timestamp: lightweightState.timestamp,
    server_timestamp: lightweightState.timestamp,
    detection_time_ms: lightweightState.detection_ms,
    avg_detection_time_ms: lightweightState.avg_detection_ms,
    hand: null, // Simplified - metrics panel doesn't need hand data
    pose: null,
    symbiotes: [],
    web_shots: [],
    thwip: null,
    score: { webs_shot: 0, balls_destroyed: 0, hits_taken: 0, combo: 0 },
    state: lightweightState.gesture?.detected ? 'DETECTED' : 'LOOKING',
    gesture_detected: lightweightState.gesture?.detected ?? false,
    gesture_name: lightweightState.gesture?.name ?? null,
    frame_width: lightweightState.frame_width,
    frame_height: lightweightState.frame_height,
  } as GameState : gameState;

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="text-center mb-6">
          <h1 className="text-4xl font-bold text-spidey-red mb-2">
            🕷️ Spider-Man Streaming POC
          </h1>
          <p className="text-gray-400">
            Latency & Frame Sync Testing
          </p>
        </header>

        {/* Mode Toggle */}
        <div className="flex justify-center gap-4 mb-4">
          <button
            onClick={() => setUseLightweight(false)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              !useLightweight
                ? 'bg-spidey-red text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            🐢 Full Mode (Python Logic)
          </button>
          <button
            onClick={() => setUseLightweight(true)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              useLightweight
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            ⚡ Lightweight Mode (React Logic)
          </button>
        </div>

        {/* Connection Status */}
        <div className="flex justify-center mb-4">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            isConnected 
              ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
              : 'bg-red-500/20 text-red-400 border border-red-500/50'
          }`}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>

        {/* Metrics Panel */}
        <MetricsPanel gameState={metricsState} />

        {/* Game Canvas - Switch between modes */}
        {useLightweight ? (
          <GameCanvasLightweight 
            onStateUpdate={setLightweightState}
            onConnectionChange={setIsConnected}
            overlayEnabled={overlayEnabled}
          />
        ) : (
          <GameCanvas 
            onStateUpdate={setGameState}
            onConnectionChange={setIsConnected}
            overlayEnabled={overlayEnabled}
          />
        )}

        {/* Controls */}
        <Controls 
          overlayEnabled={overlayEnabled}
          onToggleOverlay={() => setOverlayEnabled(!overlayEnabled)}
        />

        {/* Score Display - Only for full mode */}
        {!useLightweight && gameState?.score && (
          <div className="mt-6 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <h2 className="text-xl font-semibold text-white mb-3">Score</h2>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-3xl font-bold text-spidey-red">
                  {gameState.score.webs_shot}
                </div>
                <div className="text-gray-400 text-sm">Webs Shot</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-green-400">
                  {gameState.score.balls_destroyed}
                </div>
                <div className="text-gray-400 text-sm">Destroyed</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-yellow-400">
                  {gameState.score.hits_taken}
                </div>
                <div className="text-gray-400 text-sm">Hits Taken</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-purple-400">
                  {gameState.score.combo}
                </div>
                <div className="text-gray-400 text-sm">Combo</div>
              </div>
            </div>
          </div>
        )}

        {/* Mode Info */}
        <div className="mt-6 bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-2">
            {useLightweight ? '⚡ Lightweight Mode' : '🐢 Full Mode'}
          </h3>
          {useLightweight ? (
            <ul className="text-gray-400 text-sm space-y-1">
              <li>• Python sends only: hand landmarks, pose, gesture state</li>
              <li>• React handles: ball spawning, animation, collisions, scoring</li>
              <li>• Animation runs at smooth 60fps via requestAnimationFrame</li>
              <li>• Detection still runs at ~30fps (MediaPipe limited)</li>
            </ul>
          ) : (
            <ul className="text-gray-400 text-sm space-y-1">
              <li>• Python handles all game logic (symbiotes, webs, collisions)</li>
              <li>• React receives complete game state each frame</li>
              <li>• Frame rate tied to Python processing speed</li>
              <li>• More network data, but simpler frontend</li>
            </ul>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-8 text-center text-gray-500 text-sm">
          <p>POC for testing video + coordinate streaming architecture</p>
          <p className="mt-1">
            See: <code className="text-spidey-red">planning_docs/decisions/013-streaming-poc-coordinate-overlay.md</code>
          </p>
        </footer>
      </div>
    </div>
  )
}

export default App
