export function getToolUserError(error: unknown, fallback: string): string {
  if (error instanceof SyntaxError) {
    return "输入结构不是有效的 JSON，请检查后重试";
  }

  if (error instanceof Error) {
    const message = error.message.trim();
    if (/^\s*(4\d\d|5\d\d)\b/.test(message)) {
      return fallback;
    }
  }

  return fallback;
}
