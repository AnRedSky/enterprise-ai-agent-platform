import axios from "axios";
import { getToken } from "./auth";
import { toUserErrorMessage } from "@/utils/errorMessage";

const apiOrigin = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const request = axios.create({
  baseURL: `${apiOrigin}/api/v1`,
  timeout: 30000,
});

request.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("enterprise_agent_access_token");
      localStorage.removeItem("enterprise_agent_roles");
    }
    error.message = toUserErrorMessage(error, "请求处理失败，请稍后重试");
    return Promise.reject(error);
  },
);
