interface ControlsProps {
  overlayEnabled: boolean;
  onToggleOverlay: () => void;
}

export default function Controls({ overlayEnabled, onToggleOverlay }: ControlsProps) {
  const handleLatencyTest = async () => {
    const start = performance.now();
    
    try {
      const response = await fetch('/api/latency-test');
      const data = await response.json();
      
      const end = performance.now();
      const roundTrip = Math.round(end - start);
      const serverTime = data.server_time_ms;
      const oneWay = Math.round((end - serverTime) / 2);
      
      alert(
        `🕐 Latency Test Results:\n\n` +
        `Round-trip: ${roundTrip}ms\n` +
        `Estimated one-way: ${oneWay}ms\n` +
        `Server time: ${data.server_time_iso}`
      );
    } catch (error) {
      alert('Failed to test latency: ' + error);
    }
  };

  return (
    <div className="flex justify-center gap-4 mt-6">
      {/* Toggle Overlay */}
      <button
        onClick={onToggleOverlay}
        className={`px-6 py-3 rounded-lg font-semibold transition-all ${
          overlayEnabled
            ? 'bg-spidey-red text-white hover:bg-red-700'
            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
        }`}
      >
        {overlayEnabled ? '🎨 Overlay: ON' : '👁️ Overlay: OFF'}
      </button>

      {/* Latency Test */}
      <button
        onClick={handleLatencyTest}
        className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all"
      >
        🕐 Test Latency
      </button>

      {/* Health Check */}
      <button
        onClick={async () => {
          try {
            const response = await fetch('/api/health');
            const data = await response.json();
            alert(
              `🏥 Health Check:\n\n` +
              `Status: ${data.status}\n` +
              `Video streaming: ${data.video_streaming}\n` +
              `Frame ID: ${data.frame_id}`
            );
          } catch (error) {
            alert('Health check failed: ' + error);
          }
        }}
        className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-all"
      >
        🏥 Health Check
      </button>
    </div>
  );
}
