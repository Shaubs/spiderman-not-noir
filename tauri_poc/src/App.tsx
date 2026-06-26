/**
 * Spider-Man Web Shooter - Tauri App
 */

import { useState } from 'react';
import GameCanvas from './components/GameCanvas';

function App() {
  const [fps, setFps] = useState(0);
  const [state, setState] = useState('LOOKING');
  
  return (
    <div className="min-h-screen bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="text-center mb-6">
          <h1 className="text-4xl font-bold text-spidey-red mb-2">
            🕷️ Spider-Man Web Shooter
          </h1>
          <p className="text-gray-400">
            Tauri + React + Python | Show the 🤟 gesture to shoot webs!
          </p>
        </header>
        
        {/* Stats Bar */}
        <div className="flex justify-center gap-8 mb-4 text-white">
          <div className="px-4 py-2 bg-gray-800 rounded-lg">
            <span className="text-gray-400">FPS: </span>
            <span className="font-bold text-green-400">{fps.toFixed(1)}</span>
          </div>
          <div className="px-4 py-2 bg-gray-800 rounded-lg">
            <span className="text-gray-400">State: </span>
            <span className={`font-bold ${
              state === 'TRIGGERED' ? 'text-green-400' :
              state === 'DETECTED' ? 'text-yellow-400' :
              'text-gray-400'
            }`}>{state}</span>
          </div>
        </div>
        
        {/* Game Canvas */}
        <GameCanvas 
          onStatsUpdate={(f) => setFps(f)}
          onStateChange={(s) => setState(s)}
        />
        
        {/* Instructions */}
        <div className="mt-6 text-center text-gray-400">
          <p className="mb-2">
            <span className="text-yellow-400 font-bold">🤟 Spider-Man Gesture</span> = 
            Thumb, Index, and Pinky extended (Rock on!)
          </p>
          <p className="text-sm">
            Hold the gesture for 0.4s to trigger a web shot. Destroy the symbiote balls!
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
