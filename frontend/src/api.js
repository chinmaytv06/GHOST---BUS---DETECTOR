const API_URL = "http://localhost:8000"; // backend service

export async function getStatus() {
  const res = await fetch(`${API_URL}/`);
  return res.json();
}

export async function getVehicles() {
  const res = await fetch(`${API_URL}/api/vehicles`);
  return res.json();
}
