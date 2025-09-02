const API_URL = "http://localhost:8000"; // backend service

export async function getStatus() {
  const res = await fetch(`${API_URL}/`);
  return res.json();
}
