import type {
  AnalysisRun,
  AnalysisRunDetail,
  ApiKey,
  CreatedApiKey,
  AuthUser,
  ChatRequest,
  ChatResponse,
  Holding,
  HoldingsInput,
  HoldingExit,
  Trade,
  TradebookData,
  TradeExitInput,
  TradeInput,
  ImportResult,
  InvestmentProfile,
  InvestmentProfileInput,
  LatestPortfolioAnalysis,
  PortfolioAlert,
  PortfolioSnapshot,
  Recommendation,
  WatchlistInput,
  WatchlistItem,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "folio_token";
const USER_KEY = "folio_user";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function storeSession(token: string, user: AuthUser): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
  cache?: RequestCache;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = options.token === undefined ? readToken() : options.token;
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      cache: options.cache,
    });
  } catch {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail = (data as { detail?: string })?.detail;
    const error = new ApiError(
      typeof detail === "string" ? detail : `Request failed (${res.status})`,
      res.status,
    );
    if (res.status === 401 && token) {
      clearSession();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    throw error;
  }

  return data as T;
}

export const auth = {
  async register(name: string, email: string, password: string): Promise<AuthUser> {
    const res = await request<{ access_token: string; user: AuthUser }>(
      "/auth/register",
      { method: "POST", body: { name, email, password } },
    );
    storeSession(res.access_token, res.user);
    return res.user;
  },

  async login(email: string, password: string): Promise<AuthUser> {
    const res = await request<{ access_token: string; user: AuthUser }>(
      "/auth/login",
      { method: "POST", body: { email, password } },
    );
    storeSession(res.access_token, res.user);
    return res.user;
  },

  async me(token: string): Promise<AuthUser> {
    return request<AuthUser>("/auth/me", { token });
  },
};

export const api = {
  async health(): Promise<void> {
    await request<void>("/health", { token: null, cache: "no-store" });
  },

  async getSnapshot(): Promise<PortfolioSnapshot> {
    return request<PortfolioSnapshot>("/dashboard");
  },

  async getAlerts(includeDismissed = false): Promise<PortfolioAlert[]> {
    return request<PortfolioAlert[]>(`/alerts?include_dismissed=${includeDismissed}`);
  },

  async addHolding(input: HoldingsInput): Promise<Holding> {
    return request<Holding>("/holdings", { method: "POST", body: input });
  },

  async updateHolding(id: string, input: HoldingsInput): Promise<Holding> {
    return request<Holding>(`/holdings/${id}`, { method: "PUT", body: input });
  },

  async deleteHolding(id: string): Promise<void> {
    return request<void>(`/holdings/${id}`, { method: "DELETE" });
  },

  async exitHolding(
    id: string,
    input: { quantity: number; exitPrice: number },
  ): Promise<HoldingExit> {
    return request<HoldingExit>(`/holdings/${id}/exit`, {
      method: "POST",
      body: input,
    });
  },

  async exportHoldings(): Promise<string> {
    return request<string>("/holdings/export");
  },

  async importHoldings(csv: string): Promise<ImportResult> {
    return request<ImportResult>("/holdings/import", {
      method: "POST",
      body: { csv },
    });
  },

  async refreshAll(): Promise<Holding[]> {
    return request<Holding[]>("/holdings/fetch-all", { method: "POST" });
  },

  async refreshSymbol(symbol: string): Promise<void> {
    await request(`/holdings/fetch-price/${encodeURIComponent(symbol)}`, {
      method: "POST",
    });
  },

  async dismissAlert(id: string): Promise<void> {
    await request(`/alerts/${id}/dismiss`, { method: "PUT" });
  },

  async startHoldingAnalysis(holdingId: string): Promise<{ runId: string }> {
    return request<{ runId: string }>(`/analysis/holding/${holdingId}`, {
      method: "POST",
    });
  },

  async startPortfolioAnalysis(): Promise<{ runId: string }> {
    return request<{ runId: string }>("/analysis/portfolio", {
      method: "POST",
    });
  },

  async getAnalysisRun(runId: string): Promise<AnalysisRunDetail> {
    return request<AnalysisRunDetail>(`/analysis/${runId}`);
  },

  async getActiveRun(): Promise<AnalysisRun | null> {
    return request<AnalysisRun | null>("/analysis/active");
  },

  async cancelActiveRun(): Promise<AnalysisRun | null> {
    return request<AnalysisRun | null>("/analysis/active/cancel", {
      method: "POST",
    });
  },

  async getLatestHoldingAnalysis(holdingId: string): Promise<Recommendation | null> {
    try {
      return await request<Recommendation>(
        `/analysis/latest/holding/${holdingId}`,
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  async getLatestPortfolioAnalysis(): Promise<LatestPortfolioAnalysis | null> {
    try {
      return await request<LatestPortfolioAnalysis>("/analysis/latest/portfolio");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  async getProfile(): Promise<InvestmentProfile> {
    return request<InvestmentProfile>("/profile");
  },

  async updateProfile(input: InvestmentProfileInput): Promise<InvestmentProfile> {
    return request<InvestmentProfile>("/profile", {
      method: "PUT",
      body: input,
    });
  },

  async askAi(input: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/analysis/chat", {
      method: "POST",
      body: input,
    });
  },

  async getApiKeys(): Promise<ApiKey[]> {
    return request<ApiKey[]>("/auth/api-keys");
  },

  async createApiKey(name: string): Promise<CreatedApiKey> {
    return request<CreatedApiKey>("/auth/api-keys", {
      method: "POST",
      body: { name },
    });
  },

  async revokeApiKey(id: string): Promise<void> {
    return request<void>(`/auth/api-keys/${id}`, { method: "DELETE" });
  },

  async deleteApiKey(id: string): Promise<void> {
    return request<void>(`/auth/api-keys/${id}/permanent`, { method: "DELETE" });
  },

  async getWatchlist(): Promise<WatchlistItem[]> {
    return request<WatchlistItem[]>("/watchlist");
  },

  async addWatchlistItem(input: WatchlistInput): Promise<WatchlistItem> {
    return request<WatchlistItem>("/watchlist", { method: "POST", body: input });
  },

  async updateWatchlistItem(id: string, input: WatchlistInput): Promise<WatchlistItem> {
    return request<WatchlistItem>(`/watchlist/${id}`, { method: "PUT", body: input });
  },

  async deleteWatchlistItem(id: string): Promise<void> {
    return request<void>(`/watchlist/${id}`, { method: "DELETE" });
  },

  async refreshWatchlist(): Promise<WatchlistItem[]> {
    return request<WatchlistItem[]>("/watchlist/fetch-all", { method: "POST" });
  },

  async refreshWatchlistSymbol(symbol: string): Promise<void> {
    await request(`/watchlist/fetch-price/${encodeURIComponent(symbol)}`, { method: "POST" });
  },

  async getTradebook(): Promise<TradebookData> {
    return request<TradebookData>("/tradebook");
  },

  async addTrade(input: TradeInput): Promise<Trade> {
    return request<Trade>("/tradebook", { method: "POST", body: input });
  },

  async updateTrade(id: string, input: TradeInput): Promise<Trade> {
    return request<Trade>(`/tradebook/${id}`, { method: "PUT", body: input });
  },

  async deleteTrade(id: string): Promise<void> {
    return request<void>(`/tradebook/${id}`, { method: "DELETE" });
  },

  async exitTrade(id: string, input: TradeExitInput): Promise<Trade> {
    return request<Trade>(`/tradebook/${id}/exits`, { method: "POST", body: input });
  },

  async refreshTradebook(): Promise<TradebookData> {
    return request<TradebookData>("/tradebook/fetch-all", { method: "POST" });
  },
};

export interface RunStatus {
  status: AnalysisRun["status"];
  stage: string | null;
  errorMessage: string | null;
}

export async function pollRun(
  runId: string,
  onUpdate: (status: RunStatus) => void,
  timeoutMs = 1800000,
  intervalMs = 2000,
  signal?: AbortSignal,
): Promise<AnalysisRunDetail> {
  const deadline = Date.now() + timeoutMs;
  let last: AnalysisRunDetail;
  for (;;) {
    if (signal?.aborted) {
      throw new ApiError("Analysis cancelled.", 0);
    }
    last = await api.getAnalysisRun(runId);
    onUpdate({
      status: last.status,
      stage: last.stage,
      errorMessage: last.errorMessage,
    });
    if (
      last.status === "COMPLETED" ||
      last.status === "PARTIAL_COMPLETION" ||
      last.status === "FAILED"
    ) {
      return last;
    }
    if (Date.now() >= deadline) {
      throw new ApiError("Analysis timed out. Try again shortly.", 0);
    }
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        signal?.removeEventListener("abort", onAbort);
        resolve();
      }, intervalMs);
      const onAbort = () => {
        clearTimeout(timer);
        reject(new ApiError("Analysis cancelled.", 0));
      };
      if (signal?.aborted) {
        onAbort();
        return;
      }
      signal?.addEventListener("abort", onAbort, { once: true });
    });
  }
}
