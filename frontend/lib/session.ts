"use client";

const KEY = "fpl_session_id";

/**
 * Returns a stable anonymous session ID stored in localStorage.
 * Generated once on first visit, persisted across page loads.
 * No auth, no cookies — purely for vote deduplication.
 */
export function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";

  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}
