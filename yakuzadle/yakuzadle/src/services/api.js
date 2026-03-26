

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:3001";

export async function guessCharacter(name) {
  const res = await fetch(`${API_BASE}/guess?name=${encodeURIComponent(name)}`);
  return res.json();
}

export async function setDebugTarget(name) {
  const res = await fetch(`${API_BASE}/debug-set-target?name=${encodeURIComponent(name)}`);
  if (!res.ok) {
    throw new Error("Failed to set debug target");
  }
  return res.json();
}