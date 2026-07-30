const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export function startResearch({ query, depth, audience }) {
  return request("/api/research", {
    method: "POST",
    body: JSON.stringify({ query, depth, audience }),
  });
}

export function getJob(jobId) {
  return request(`/api/research/${jobId}`);
}

export function checkHealth() {
  return request("/api/health");
}
