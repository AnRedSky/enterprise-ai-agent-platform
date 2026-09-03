import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const source = readFileSync(resolve(root, "src/views/login/components/LoginForm.vue"), "utf8");

describe("LoginForm shared presentation contract", () => {
  it("uses the shared surface primitive instead of a raw Element Plus card", () => {
    expect(source).toContain('import SurfaceCard from "@/components/ui/SurfaceCard.vue"');
    expect(source).toContain("<SurfaceCard class=\"login-card\"");
    expect(source).not.toMatch(/<el-card\b/);
  });

  it("keeps the login interaction and API boundary intact", () => {
    expect(source).toContain('import { login } from "../../../api/auth"');
    expect(source).toContain("await login(form.username, form.password)");
    expect(source).toContain('await router.replace("/dashboard")');
    expect(source).toContain("请输入用户名和密码");
    expect(source).toContain("登录失败，请检查用户名和密码");
  });

  it("uses responsive shared design tokens for the login surface", () => {
    expect(source).toContain("var(--ui-bg-app)");
    expect(source).toContain("width: min(420px, 100%)");
    expect(source).toContain("padding: 24px 16px");
  });
});
