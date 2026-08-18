import { beforeEach } from "vitest";
function createStorage() {
    let values = new Map();
    return {
        get length() {
            return values.size;
        },
        clear() {
            values.clear();
        },
        getItem(key) {
            return values.get(key) ?? null;
        },
        key(index) {
            return Array.from(values.keys())[index] ?? null;
        },
        removeItem(key) {
            values.delete(key);
        },
        setItem(key, value) {
            values.set(String(key), String(value));
        },
    };
}
beforeEach(() => {
    if (!globalThis.localStorage) {
        Object.defineProperty(globalThis, "localStorage", {
            configurable: true,
            value: createStorage(),
        });
    }
});
