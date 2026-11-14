const KEY = "retrace.key";

export const auth = {
  get: () => sessionStorage.getItem(KEY) || "",
  set: (v) => sessionStorage.setItem(KEY, v),
  clear: () => sessionStorage.removeItem(KEY),
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function messageFrom(body, fallback) {
  if (!body || body.detail == null) return fallback;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join(". ");
  return fallback;
}

export async function api(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const key = auth.get();
  if (key) headers.Authorization = `Bearer ${key}`;

  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
  }
  if (res.status === 401 && !path.startsWith("/respond")) window.dispatchEvent(new Event("retrace:unauthorized"));
  if (!res.ok) {
    let parsed = null;
    try { parsed = await res.json(); } catch { /* non-JSON error body */ }
    throw new ApiError(messageFrom(parsed, `Request failed (${res.status}).`), res.status);
  }
  if (res.status === 204) return null;
  return raw ? res : res.json();
}

export async function downloadMarkdown(id) {
  const res = await api(`/incidents/${id}/report.md`, { raw: true });
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: `incident-${id}.md` });
  a.click();
  URL.revokeObjectURL(url);
}
