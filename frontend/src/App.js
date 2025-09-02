import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { connect } from "./wsClient";
import "leaflet/dist/leaflet.css";

// ✅ Fix Leaflet icon issue (fallback to default if custom icon fails)
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

const busIcon = new L.Icon({
  iconUrl: "https://www.pngmart.com/files/23/Bus-Icon-PNG-Isolated-HD.png", // Bus icon
  iconSize: [30, 30], // bigger so it's visible
});

function App() {
  const [vehicles, setVehicles] = useState([]);

  useEffect(() => {
    connect((data) => {
      setVehicles((prev) => {
        const updated = prev.filter((v) => v.vehicle_id !== data.vehicle_id);
        return [...updated, data];
      });
    });
  }, []);

  return (
    <MapContainer
      center={[12.9716, 77.5946]}
      zoom={14}
      style={{ height: "100vh", width: "100%" }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />

      {vehicles.map((v) => (
        <Marker key={v.vehicle_id} position={[v.lat, v.lon]} icon={busIcon}>
          <Popup>
            <b>ID:</b> {v.vehicle_id} <br />
            <b>Route:</b> {v.route_id} <br />
            <b>Speed:</b> {v.speed || "N/A"} m/s
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

export default App;
