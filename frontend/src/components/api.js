// All backend access goes through here. VITE_API_BASE is only needed if the
// API is hosted on a different origin than the UI (not the case in Docker).
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function get(path, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  const res = await fetch(`${BASE}/api${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  config: () => get("/config"),
  decision: (day, cutoff) => get("/decision", { day, cutoff }),
  metrics: (cutoff) => get("/metrics", { cutoff }),
  daily: (cutoff) => get("/metrics/daily", { cutoff }),
  byHour: (cutoff) => get("/metrics/by-hour", { cutoff }),
  byHorizon: () => get("/metrics/by-horizon"),
  errors: (cutoff) => get("/errors", { cutoff }),
};
