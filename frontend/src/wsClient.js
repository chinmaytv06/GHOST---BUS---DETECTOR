const WS_URL =
  process.env.REACT_APP_WS_URL || `ws://${window.location.hostname}:8000/ws/vehicles`;

export function connect(onMessage) {
  const socket = new WebSocket(WS_URL);

  socket.onopen = () => console.log("✅ WebSocket connected");

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("📡 Received:", data);
      onMessage(data);
    } catch (err) {
      console.error("⚠️ Error parsing message:", err);
    }
  };

  socket.onclose = () => console.log("❌ WebSocket disconnected");
  socket.onerror = (err) => console.error("⚠️ WebSocket error:", err);

  return socket;
}
