import { beforeEach } from "vitest";

function createStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(String(key), String(value));
    },
  } as Storage;
}

// Node 25+ exposes a guarded global localStorage accessor which emits an
// ExperimentalWarning when no --localstorage-file is supplied. Define the
// test storage before anything reads that accessor so Vitest/jsdom tests stay
// deterministic without requiring a Node process flag.
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  writable: true,
  value: createStorage(),
});

beforeEach(() => {
  globalThis.localStorage.clear();
});
