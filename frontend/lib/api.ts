"use client";

import axios, { AxiosError } from "axios";
import toast from "react-hot-toast";

import type {
  AgentTaskStatusResponse,
  AgentsStatusResponse,
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  DeleteRepoResponse,
  IndexRequest,
  ReadmeGenerateRequest,
  ReadmeResponse,
  RepoFilesResponse,
  RepoIndexQueuedResponse,
  RepoStatusResponse,
  RepositoryIndexRequest,
  TaskQueuedResponse,
} from "@/lib/types";

type AuthTokenProvider = () => Promise<string | null>;

let authTokenProvider: AuthTokenProvider | null = null;

export function setAuthTokenProvider(provider: AuthTokenProvider | null) {
  authTokenProvider = provider;
}

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  if (authTokenProvider) {
    const token = await authTokenProvider();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    const message =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      "Request failed.";

    const suppressToast = error.config?.headers?.["x-suppress-toast"] === "1";
    if (typeof window !== "undefined" && !suppressToast) {
      toast.error(String(message));
    }

    return Promise.reject(error);
  },
);

export async function indexRepository(payload: IndexRequest): Promise<RepoIndexQueuedResponse> {
  const response = await api.post<RepoIndexQueuedResponse>("/api/v1/repos/index", payload);
  return response.data;
}

export async function createRepositoryIndex(
  payload: RepositoryIndexRequest,
): Promise<RepoIndexQueuedResponse> {
  return indexRepository({
    github_url: payload.repository_url,
    repo_id: payload.repo_id,
  });
}

export async function getRepositoryStatus(repoId: string): Promise<RepoStatusResponse> {
  const response = await api.get<RepoStatusResponse>(`/api/v1/repos/${encodeURIComponent(repoId)}/status`);
  return response.data;
}

export async function getRepositoryFiles(repoId: string): Promise<RepoFilesResponse> {
  const response = await api.get<RepoFilesResponse>(`/api/v1/repos/${encodeURIComponent(repoId)}/files`);
  return response.data;
}

export async function deleteRepository(repoId: string): Promise<DeleteRepoResponse> {
  const response = await api.delete<DeleteRepoResponse>(`/api/v1/repos/${encodeURIComponent(repoId)}`);
  return response.data;
}

export async function askRepositoryQuestion(payload: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>("/api/v1/chat", payload);
  return response.data;
}

export async function streamRepositoryQuestion(
  payload: ChatRequest,
  onChunk: (chunk: string) => void,
): Promise<void> {
  const token = authTokenProvider ? await authTokenProvider() : null;
  const response = await fetch(`${api.defaults.baseURL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ ...payload, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`Streaming request failed with status ${response.status}.`);
  }

  if (!response.body) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    onChunk(decoder.decode(value, { stream: true }));
  }
}

export async function getChatHistory(repoId: string): Promise<ChatHistoryResponse> {
  const response = await api.get<ChatHistoryResponse>(`/api/v1/chat/history/${encodeURIComponent(repoId)}`);
  return response.data;
}

export async function generateReadme(payload: ReadmeGenerateRequest): Promise<TaskQueuedResponse> {
  const response = await api.post<TaskQueuedResponse>("/api/v1/readme/generate", payload);
  return response.data;
}

export async function getReadme(repoId: string): Promise<ReadmeResponse> {
  const response = await api.get<ReadmeResponse>(`/api/v1/readme/${encodeURIComponent(repoId)}`, {
    headers: { "x-suppress-toast": "1" },
  });
  return response.data;
}

export async function getAgentStatus(): Promise<AgentsStatusResponse> {
  const response = await api.get<AgentsStatusResponse>("/api/v1/agents/status");
  return response.data;
}

export async function getAgentTaskStatus(taskId: string): Promise<AgentTaskStatusResponse> {
  const response = await api.get<AgentTaskStatusResponse>(`/api/v1/agents/status/${encodeURIComponent(taskId)}`);
  return response.data;
}
