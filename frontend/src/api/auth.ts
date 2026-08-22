import { request } from "./request";

const TOKEN_KEY = "enterprise_agent_access_token";
const ROLES_KEY = "enterprise_agent_roles";
const USER_ID_KEY = "enterprise_agent_user_id";

export type LoginResponse = {
  user_id: string;
  access_token: string;
  token_type: string;
  roles: string[];
};

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUserId() {
  return localStorage.getItem(USER_ID_KEY);
}

export function getRoles(): string[] {
  try {
    return JSON.parse(localStorage.getItem(ROLES_KEY) || "[]");
  } catch {
    return [];
  }
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function setSession(data: LoginResponse) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(ROLES_KEY, JSON.stringify(data.roles || []));
  localStorage.setItem(USER_ID_KEY, data.user_id);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLES_KEY);
  localStorage.removeItem(USER_ID_KEY);
}

export async function login(username: string, password: string) {
  const response = await request.post<LoginResponse>("/auth/login", { username, password });
  setSession(response.data);
  return response.data;
}

export async function register(username: string, password: string) {
  return (await request.post("/auth/register", { username, password })).data;
}
