export interface ApiErrorLike {
  message?: string;
  response?: {
    status?: number;
    data?: {
      detail?: string;
      message?: string;
      error?: { code?: string; message?: string };
    };
  };
}

const statusMessage: Record<number, string> = {
  400: "请求参数有误，请检查填写内容后重试",
  401: "登录状态已失效，请重新登录",
  403: "当前账号没有执行此操作的权限",
  404: "请求的资源不存在，请刷新后重试",
  409: "当前数据已发生变化，请刷新后重试",
  422: "提交的数据未通过校验，请检查后重试",
  429: "请求过于频繁，请稍后再试",
};

function backendMessage(error: ApiErrorLike): string | undefined {
  const data = error.response?.data;
  if (!data) return undefined;
  return data.error?.message || data.message || data.detail;
}

export function toUserErrorMessage(error: unknown, fallback = "请求处理失败，请稍后重试"): string {
  const candidate = (error && typeof error === "object" ? error : {}) as ApiErrorLike;
  const status = candidate.response?.status;
  if (status && statusMessage[status]) return statusMessage[status];
  if (status && status >= 500) return "服务暂时不可用，请稍后重试";
  if (status) return "请求处理失败，请稍后重试";

  const message = backendMessage(candidate);
  if (message && !/^\s*(?:HTTP\s*)?[45]\d\d\b/i.test(message)) return message;
  if (candidate.message && !/^\s*(?:HTTP\s*)?[45]\d\d\b/i.test(candidate.message)) return candidate.message;
  return fallback;
}
