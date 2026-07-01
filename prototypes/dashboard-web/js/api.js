// Thin HTTP client for the DreamWork dashboard.
// Talks to the live backend served from the same origin under the /api prefix.
// Everything else (data shaping, display extras) lives in data.js.

const API_BASE = "/api";

async function apiGet(path) {
  const r = await fetch(API_BASE + path);
  if (!r.ok) throw new Error(r.status + " " + path);
  return r.json();
}

async function apiPatch(path, body) {
  const r = await fetch(API_BASE + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.status + " " + path);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.status + " " + path);
  return r.json();
}
