import { beforeEach, describe, expect, it } from "vitest";
import { clearSession, getRoles, getToken, isAuthenticated, setSession } from "./auth";
describe("auth session", () => {
    beforeEach(() => {
        localStorage.clear();
    });
    it("stores and clears bearer session", () => {
        setSession({ access_token: "token-123", token_type: "bearer", roles: ["user"] });
        expect(getToken()).toBe("token-123");
        expect(getRoles()).toEqual(["user"]);
        expect(isAuthenticated()).toBe(true);
        clearSession();
        expect(getToken()).toBeNull();
        expect(getRoles()).toEqual([]);
        expect(isAuthenticated()).toBe(false);
    });
    it("recovers from malformed role storage", () => {
        localStorage.setItem("enterprise_agent_roles", "invalid-json");
        expect(getRoles()).toEqual([]);
    });
});
