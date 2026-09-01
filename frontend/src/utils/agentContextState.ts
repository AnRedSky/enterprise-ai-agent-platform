export type AgentContextState = "loading" | "empty" | "error" | "permission" | "success";

export interface AgentContextResult<T> {
  state: AgentContextState;
  data: T | null;
  errorMessage: string;
}

interface ErrorLike {
  response?: {
    status?: unknown;
    data?: {
      status?: unknown;
      code?: unknown;
    };
  };
  status?: unknown;
  code?: unknown;
  message?: unknown;
}

export function isAgentPermissionError(value: unknown): boolean {
  if (typeof value === "string") return /403|forbidden/i.test(value);
  if (!value || typeof value !== "object") return false;
  const error = value as ErrorLike;
  const status = error.response?.status ?? error.response?.data?.status ?? error.status;
  const code = error.response?.data?.code ?? error.code;
  return status === 403 || status === "403" || code === "FORBIDDEN" || code === "403";
}

export async function loadAgentContext<T>(loader: () => Promise<T>): Promise<AgentContextResult<T>> {
  try {
    const data = await loader();
    return {
      state: data ? "success" : "empty",
      data: data || null,
      errorMessage: "",
    };
  } catch (error) {
    if (isAgentPermissionError(error)) {
      return { state: "permission", data: null, errorMessage: "无权加载调试配置" };
    }
    return { state: "error", data: null, errorMessage: "当前生效配置加载失败，请稍后重试" };
  }
}
