/**
 * localStorage saves plus file export/import.
 *
 * Every value stored under the `los.save.` prefix is exactly the JSON text
 * `EngineBridge.save()` returns (`save_manager.serialize()`), so a save made in the
 * browser loads in the console build and vice versa (web_contract.md 1). The only thing
 * this module changes client-side is the `label` field, because `GameSession.save()` has
 * no parameter for it.
 *
 * Every localStorage access is wrapped in try/catch: private browsing, a full quota or a
 * disabled storage API must degrade to "no saves", never to a crash.
 */

export const SAVE_PREFIX = "los.save.";
export const AUTOSAVE_KEY = SAVE_PREFIX + "autosave";

export interface SaveMeta {
  /** Full localStorage key, e.g. `los.save.autosave`. */
  key: string;
  label: string;
  generation: number;
  year: number;
  director: string;
  /** ISO timestamp from `save_manager.serialize`, or "" if missing. */
  savedAt: string;
  gameOver: boolean;
}

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

function safeKeys(): string[] {
  const keys: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (key && key.startsWith(SAVE_PREFIX)) keys.push(key);
    }
  } catch {
    /* localStorage unavailable: report no saves rather than throw */
  }
  return keys;
}

/** Overrides the `label` field of a save file's JSON text (the bridge always writes ""). */
export function withLabel(saveText: string, label: string): string {
  try {
    const payload = JSON.parse(saveText) as Record<string, unknown>;
    payload["label"] = label;
    return JSON.stringify(payload, null, 2);
  } catch {
    return saveText;
  }
}

function parseMeta(key: string, text: string): SaveMeta | null {
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
  if (typeof payload !== "object" || payload === null || !("program" in payload)) return null;
  const label = typeof payload["label"] === "string" && payload["label"] ? (payload["label"] as string) : key.slice(SAVE_PREFIX.length);
  return {
    key,
    label,
    generation: Number(payload["generation"] ?? 0),
    year: Number(payload["year"] ?? 0),
    director: typeof payload["director"] === "string" ? (payload["director"] as string) : "",
    savedAt: typeof payload["saved_at"] === "string" ? (payload["saved_at"] as string) : "",
    gameOver: Boolean(payload["game_over"]),
  };
}

/** All saves in localStorage, newest first. Unreadable entries are skipped. */
export function listSaves(): SaveMeta[] {
  const metas: SaveMeta[] = [];
  for (const key of safeKeys()) {
    const text = safeGet(key);
    if (!text) continue;
    const meta = parseMeta(key, text);
    if (meta) metas.push(meta);
  }
  metas.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  return metas;
}

export function loadSaveText(key: string): string | null {
  return safeGet(key);
}

/** Writes (or overwrites) one slot, e.g. the fixed "autosave" id. Returns false on failure. */
export function saveToSlot(id: string, text: string): boolean {
  return safeSet(SAVE_PREFIX + id, text);
}

/** Creates a new manual save under a fresh key and returns it. `text` should already carry
 *  the chosen label (see `withLabel`). Returns null on failure. */
export function saveNew(text: string): string | null {
  const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  return safeSet(SAVE_PREFIX + id, text) ? SAVE_PREFIX + id : null;
}

export function deleteSave(key: string): void {
  safeRemove(key);
}

/** Downloads the given save text as a JSON file. */
export function exportSave(text: string, filename: string): void {
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/** Reads a File (from an <input type="file">) as text - the same JSON `save()` produces. */
export function importSaveFile(file: File): Promise<string> {
  return file.text();
}
