import { describe, expect, it } from "vitest";
import { toUserErrorMessage } from "../../src/utils/errorMessage";

describe("toUserErrorMessage", () => {
  it("maps HTTP status errors to Chinese user-facing messages", () => {
    expect(toUserErrorMessage({ response: { status: 401 } })).toBe("登录状态已失效，请重新登录");
    expect(toUserErrorMessage({ response: { status: 404 } })).toBe("请求的资源不存在，请刷新后重试");
    expect(toUserErrorMessage({ response: { status: 503 } })).toBe("服务暂时不可用，请稍后重试");
  });

  it("does not expose raw HTTP error messages", () => {
    expect(toUserErrorMessage({ message: "HTTP 502 Bad Gateway" })).toBe("请求处理失败，请稍后重试");
    expect(toUserErrorMessage({ response: { status: 500 }, message: "Internal Server Error" })).toBe("服务暂时不可用，请稍后重试");
  });

  it("keeps useful backend business messages", () => {
    expect(toUserErrorMessage({ response: { status: 400, data: { message: "名称不能为空" } } })).toBe("请求参数有误，请检查填写内容后重试");
    expect(toUserErrorMessage({ response: { data: { error: { code: "MODEL_NOT_READY", message: "模型尚未就绪" } } } })).toBe("模型尚未就绪");
  });

  it("uses the caller fallback when no readable error is available", () => {
    expect(toUserErrorMessage(undefined, "智能体加载失败，请刷新后重试")).toBe("智能体加载失败，请刷新后重试");
  });
});
