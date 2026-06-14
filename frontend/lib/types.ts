export type IndexRequest = {
  github_url: string;
  repo_id?: string | null;
};

export type RepositoryIndexRequest = {
  repository_url: string;
  branch?: string;
  repo_id?: string;
};

export type IndexResult = {
  repo_id: string;
  commit_sha: string;
  total_files: number;
  total_chunks: number;
  file_list: string[];
};

export type RepoIndexQueuedResponse = {
  repo_id: string;
  task_id: string;
  status: "queued" | "ready";
  result?: IndexResult | null;
};

export type RepositoryIndexResponse = RepoIndexQueuedResponse;

export type RepoStatusResponse = {
  repo_id: string;
  status: "indexing" | "ready" | "failed";
  meta: {
    url?: string;
    commit_sha?: string;
    indexed_at?: string;
    last_accessed_at?: string;
    file_count?: number;
    chunk_count?: number;
    [key: string]: unknown;
  } | null;
};

export type RepoFileInfo = {
  file_path: string;
  language: string;
  chunk_count: number;
};

export type RepoFilesResponse = {
  repo_id: string;
  files: RepoFileInfo[];
};

export type DeleteRepoResponse = {
  repo_id: string;
  deleted: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type ChatRequest = {
  repo_id: string;
  question: string;
  message?: string;
  stream?: boolean;
  history?: ChatMessage[];
  top_k?: number;
};

export type CodeCitation = {
  repo_id?: string;
  file_path: string;
  start_line: number;
  end_line: number;
  score?: number;
  text?: string | null;
};

export type Citation = {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  relevance: string;
};

export type SourceCitation = Citation | CodeCitation;

export type ChatResponse = {
  repo_id?: string | null;
  answer: string;
  citations: SourceCitation[];
  confidence: number;
  intent: string;
  active_agents: string[];
  agent_trace: string[];
};

export type ChatHistoryItem = {
  question: string;
  answer: string;
  confidence: number;
  intent: string;
  created_at: string;
  citations: SourceCitation[];
};

export type ChatHistoryResponse = {
  history: ChatHistoryItem[];
};

export type ReadmeGenerateRequest = {
  repo_id: string;
  force_regenerate?: boolean;
};

export type ReadmeRequest = ReadmeGenerateRequest & {
  audience?: string;
  include_setup?: boolean;
  include_architecture?: boolean;
  include_deployment?: boolean;
};

export type TaskQueuedResponse = {
  task_id: string;
  status: "queued";
};

export type ReadmeResponse = {
  repo_id?: string | null;
  content: string;
  markdown?: string | null;
  generated_at: string;
  confidence: number;
  format: "markdown";
};

export type AgentStatus = {
  name: string;
  status: string;
  detail?: string | null;
};

export type AgentsStatusResponse = {
  agents: AgentStatus[];
};

export type AgentTaskStatusResponse = {
  task_id: string;
  status: string;
  progress: number;
  percent?: number;
  current_agent: string;
  completed_steps: string[];
  current_step?: string | null;
  message?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
};
