import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { connect } from "./wsClient";
import { getVehicles } from "./api";
import "leaflet/dist/leaflet.css";

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
  iconUrl: "https://www.pngmart.com/files/23/Bus-Icon-PNG-Isolated-HD.png",
  iconSize: [30, 30],
});

const ghostBusIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/616/616408.png",
  iconSize: [30, 30],
});

const recurringGhostIcon = new L.Icon({
  iconUrl: "https://cdn-icons-png.flaticon.com/512/3863/3863499.png",
  iconSize: [35, 35],
});

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [showGhostOnly, setShowGhostOnly] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState("");
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const [routes, setRoutes] = useState([]);

  useEffect(() => {
    connect((data) => {
      const parsedLat = Number(data.lat);
      const parsedLon = Number(data.lon);
      if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLon)) {
        console.warn('Skipping invalid vehicle data:', data.vehicle_id, { lat: data.lat, lon: data.lon });
        return;
      }
      const parsedData = {
        ...data,
        lat: parsedLat,
        lon: parsedLon
      };
      setVehicles((prev) => {
        const updated = prev.filter((v) => v.vehicle_id !== parsedData.vehicle_id);
        return [...updated, parsedData];
      });
    }, (status) => {
      setConnectionStatus(status);
    });

    // Fetch initial vehicles
    const loadInitialVehicles = async () => {
      try {
        const response = await getVehicles();
        if (response.vehicles) {
          const parsedVehicles = response.vehicles.map(v => ({
            ...v,
            lat: Number(v.lat),
            lon: Number(v.lon)
          })).filter(v => Number.isFinite(v.lat) && Number.isFinite(v.lon));
          const skipped = response.vehicles.length - parsedVehicles.length;
          if (skipped > 0) {
            console.warn(`Skipped ${skipped} invalid vehicles during initial load`);
          }
          setVehicles(parsedVehicles);
        }
      } catch (error) {
        console.error("Failed to load initial vehicles:", error);
      }
    };

    loadInitialVehicles();
  }, []);

  // Extract unique routes from vehicles
  useEffect(() => {
    const uniqueRoutes = [...new Set(vehicles.map(v => v.route_id).filter(Boolean))];
    setRoutes(uniqueRoutes);
  }, [vehicles]);

  const filteredVehicles = vehicles.filter((v) => {
    if (showGhostOnly && !v.is_ghost) return false;
    if (selectedRoute && v.route_id !== selectedRoute) return false;
    // Additional safeguard, though parsing should ensure validity
    if (!Number.isFinite(v.lat) || !Number.isFinite(v.lon)) return false;
    return true;
  });

  const total = filteredVehicles.length;
  const ghostCount = filteredVehicles.filter((v) => v.is_ghost).length;
  const recurringGhostCount = filteredVehicles.filter((v) => v.is_recurring_ghost).length;
  const normalCount = total - ghostCount;

  const getMarkerIcon = (vehicle) => {
    if (vehicle.is_recurring_ghost) return recurringGhostIcon;
    if (vehicle.is_ghost) return ghostBusIcon;
    return busIcon;
  };

  const getStatusColor = (vehicle) => {
    if (vehicle.is_recurring_ghost) return "#8B0000"; // Dark red
    if (vehicle.is_ghost) return "#FF0000"; // Red
    return "#00FF00"; // Green
  };

  return (
    <>
      <div style={{
        position: "absolute",
        top: 10,
        left: 10,
        zIndex: 1000,
        backgroundColor: "white",
        padding: "15px",
        borderRadius: "8px",
        boxShadow: "0 0 15px rgba(0,0,0,0.3)",
        fontFamily: "Arial, sans-serif",
        width: "280px",
        maxHeight: "80vh",
        overflowY: "auto"
      }}>
        <h3 style={{ marginTop: 0, color: "#333" }}>🚍 Ghost Bus Monitor</h3>
        <p style={{ fontSize: "12px", color: "#666" }}><b>Connection:</b> {connectionStatus}</p>

        <div style={{ marginBottom: "15px" }}>
          <h4 style={{ margin: "5px 0", color: "#333" }}>Statistics</h4>
          <p style={{ margin: "2px 0" }}>Total Buses: <b>{total}</b></p>
          <p style={{ margin: "2px 0", color: "#8B0000" }}>
            <span role="img" aria-label="recurring-ghost">👻🔄</span> Recurring Ghosts: <b>{recurringGhostCount}</b>
          </p>
          <p style={{ margin: "2px 0", color: "#FF0000" }}>
            <span role="img" aria-label="ghost">👻</span> Ghost Buses: <b>{ghostCount}</b> ({((ghostCount / total) * 100 || 0).toFixed(0)}%)
          </p>
          <p style={{ margin: "2px 0", color: "#00AA00" }}>
            <span role="img" aria-label="normal">✔️</span> Normal: <b>{normalCount}</b>
          </p>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <h4 style={{ margin: "5px 0", color: "#333" }}>Filters</h4>
          <label style={{ display: "block", marginBottom: "8px" }}>
            <input
              type="checkbox"
              checked={showGhostOnly}
              onChange={() => setShowGhostOnly(!showGhostOnly)}
              style={{ marginRight: "5px" }}
            />
            Show only ghost buses
          </label>

          <div style={{ marginTop: "8px" }}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px" }}>
              Filter by Route:
            </label>
            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              style={{
                width: "100%",
                padding: "4px",
                borderRadius: "4px",
                border: "1px solid #ccc",
                fontSize: "12px"
              }}
            >
              <option value="">All Routes</option>
              {routes.map(route => (
                <option key={route} value={route}>Route {route}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ fontSize: "11px", color: "#666", borderTop: "1px solid #eee", paddingTop: "8px" }}>
          <p style={{ margin: "2px 0" }}>🔴 Recurring Ghost</p>
          <p style={{ margin: "2px 0" }}>🟠 Ghost Bus</p>
          <p style={{ margin: "2px 0" }}>🟢 Normal Bus</p>
        </div>
      </div>

      <MapContainer
        center={[42.3601, -71.0589]}
        zoom={11}
        style={{ height: "100vh", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />

        {filteredVehicles.map((v) => {
          // Final safeguard
          if (!Number.isFinite(v.lat) || !Number.isFinite(v.lon)) {
            console.warn('Skipping Marker for invalid vehicle:', v.vehicle_id);
            return null;
          }
          return (
            <Marker
              key={v.vehicle_id}
              position={[v.lat, v.lon]}
              icon={getMarkerIcon(v)}
            >
              <Popup>
                <div style={{
                  fontFamily: "Arial, sans-serif",
                  fontSize: "14px",
                  maxWidth: "250px"
                }}>
                  <h4 style={{
                    margin: "0 0 8px 0",
                    color: getStatusColor(v),
                    borderBottom: "1px solid #eee",
                    paddingBottom: "4px"
                  }}>
                    {v.is_recurring_ghost ? "🔴 Recurring Ghost Bus" :
                     v.is_ghost ? "🟠 Ghost Bus" : "🟢 Normal Bus"}
                  </h4>

                  <div style={{ marginBottom: "8px" }}>
                    <strong>Vehicle ID:</strong> {v.vehicle_id}<br/>
                    <strong>Route:</strong> {v.route_id || "N/A"}<br/>
                    <strong>Trip:</strong> {v.trip_id || "N/A"}<br/>
                    <strong>Speed:</strong> {v.speed ? `${v.speed.toFixed(1)} m/s` : "N/A"}<br/>
                    <strong>Ghost Score:</strong>
                    <span style={{
                      color: v.ghost_score > 50 ? "#FF0000" : v.ghost_score > 20 ? "#FFA500" : "#00AA00",
                      fontWeight: "bold"
                    }}>
                      {v.ghost_score || 0}/100
                    </span>
                  </div>

                  {v.detection_rules && (
                    <div style={{ fontSize: "12px", color: "#666" }}>
                      <strong>Detection Rules:</strong><br/>
                      {v.detection_rules.stale && <span>⏰ Stale data<br/></span>}
                      {v.detection_rules.stationary && <span>📍 Stationary<br/></span>}
                      {v.detection_rules.off_route && <span>🗺️ Off route<br/></span>}
                    </div>
                  )}

                  <div style={{
                    marginTop: "8px",
                    fontSize: "11px",
                    color: "#888",
                    borderTop: "1px solid #eee",
                    paddingTop: "4px"
                  }}>
                    Last updated: {new Date((v.timestamp || 0) * 1000).toLocaleTimeString()}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </>
  );
}

export default App;
