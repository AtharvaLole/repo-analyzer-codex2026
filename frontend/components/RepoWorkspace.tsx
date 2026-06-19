"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpenText,
  Bot,
  CheckCircle2,
  Clock3,
  FileCode2,
  FileStack,
  GitCommitHorizontal,
  Layers3,
  MessageSquareText,
  SearchCode,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { ChatWindow } from "@/components/ChatWindow";
import { FileTree } from "@/components/FileTree";
import { ReadmePreview } from "@/components/ReadmePreview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getRepositoryFiles, getRepositoryStatus } from "@/lib/api";
import { repoTypeLabel, suggestedQuestionsForFiles } from "@/lib/repo-insights";
import { cn } from "@/lib/utils";

type RepoWorkspaceProps = {
  repoId: string;
};

type TabKey = "chat" | "readme" | "security" | "files";

const tabs: Array<{ key: TabKey; label: string; icon: typeof MessageSquareText }> = [
  { key: "chat", label: "Chat", icon: MessageSquareText },
  { key: "readme", label: "README", icon: BookOpenText },
  { key: "security", label: "Security", icon: ShieldCheck },
  { key: "files", label: "Files", icon: FileCode2 },
];

export function RepoWorkspace({ repoId }: RepoWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const [selectedPath, setSelectedPath] = useState<string | undefined>();

  const statusQuery = useQuery({
    queryKey: ["repo-status", repoId],
    queryFn: () => getRepositoryStatus(repoId),
    refetchInterval: (query) => (query.state.data?.status === "indexing" ? 3000 : false),
  });

  const filesQuery = useQuery({
    queryKey: ["repo-files", repoId],
    queryFn: () => getRepositoryFiles(repoId),
  });

  const files = filesQuery.data?.files ?? [];
  const suggestions = useMemo(() => suggestedQuestionsForFiles(files), [files]);
  const repoType = repoTypeLabel(files);
  const meta = statusQuery.data?.meta;
  const status = statusQuery.data?.status ?? "loading";
  const fileCount = meta?.file_count ?? files.length;
  const chunkCount = meta?.chunk_count;
  const languageSummary = useMemo(() => summarizeLanguages(files), [files]);
  const priorityFiles = useMemo(
    () => [...files].sort((a, b) => b.chunk_count - a.chunk_count).slice(0, 4),
    [files],
  );
  const completion = analysisCompletion(status, files.length, chunkCount);
  const stages = analysisStages(status, files.length, chunkCount);

  return (
    <motion.div className="space-y-5" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <header className="overflow-hidden rounded-lg border bg-card shadow-sm">
        <div className="border-b bg-muted/30 px-5 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <SearchCode className="h-4 w-4" aria-hidden="true" />
              </span>
              Analysis workspace
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
              Last indexed {formatDate(String(meta?.indexed_at ?? ""))}
            </div>
          </div>
        </div>

        <div className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-primary/10 text-primary ring-primary/20">{repoType}</Badge>
              <StatusBadge status={status} />
            </div>
            <h1 className="mt-3 truncate text-2xl font-semibold tracking-normal">{meta?.url ?? repoId}</h1>
            <p className="mt-2 flex min-w-0 items-center gap-2 break-all text-sm text-muted-foreground">
              <GitCommitHorizontal className="h-4 w-4 shrink-0" aria-hidden="true" />
              Commit {meta?.commit_sha ?? "unknown"}
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <Meta icon={FileStack} label="Files" value={String(fileCount)} />
            <Meta icon={Layers3} label="Chunks" value={String(chunkCount ?? "--")} />
            <Meta icon={Sparkles} label="Questions" value={String(suggestions.length)} />
          </dl>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-md border bg-background p-4">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="font-medium">Analysis progress</span>
              <span className="text-muted-foreground">{completion}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn("h-full rounded-full", status === "failed" ? "bg-destructive" : "bg-primary")}
                initial={{ width: 0 }}
                animate={{ width: `${completion}%` }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-4">
              {stages.map((stage, index) => (
                <motion.div
                  key={stage.label}
                  className={cn(
                    "rounded-md border px-3 py-2",
                    stage.state === "done" && "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
                    stage.state === "active" && "border-primary/30 bg-primary/10 text-primary",
                  )}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.06 }}
                >
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <span className={cn("h-2 w-2 rounded-full bg-muted-foreground", stage.state === "done" && "bg-emerald-500", stage.state === "active" && "animate-pulse bg-primary")} />
                    {stage.label}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{stage.detail}</p>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="rounded-md border bg-background p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Bot className="h-4 w-4 text-primary" aria-hidden="true" />
              Ready insights
            </div>
            <div className="mt-3 space-y-2">
              {languageSummary.length ? (
                languageSummary.map((item) => (
                  <div key={item.language} className="grid grid-cols-[84px_minmax(0,1fr)_36px] items-center gap-2 text-xs">
                    <span className="truncate text-muted-foreground">{item.language}</span>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-secondary" style={{ width: `${item.percent}%` }} />
                    </div>
                    <span className="text-right font-medium">{item.count}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Language mix appears after indexing.</p>
              )}
            </div>
          </div>
        </div>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <motion.aside className="rounded-lg border bg-card p-4 shadow-sm" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.08 }}>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">Files</h2>
            <span className="text-xs text-muted-foreground">{files.length}</span>
          </div>
          <div className="max-h-[720px] overflow-auto">
            <FileTree files={files} selectedPath={selectedPath} onSelect={setSelectedPath} />
          </div>
        </motion.aside>

        <section className="min-w-0 space-y-4">
          <div className="flex flex-wrap gap-2 rounded-lg border bg-card p-2 shadow-sm">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <Button
                  key={tab.key}
                  type="button"
                  variant={activeTab === tab.key ? "default" : "ghost"}
                  className="relative isolate overflow-hidden"
                  onClick={() => setActiveTab(tab.key)}
                >
                  {activeTab === tab.key ? (
                    <motion.span layoutId="active-tab-glow" className="absolute inset-0 -z-10 rounded-md bg-primary" />
                  ) : null}
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {tab.label}
                </Button>
              );
            })}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {activeTab === "chat" ? <ChatWindow repoId={repoId} suggestedQuestions={suggestions} /> : null}
              {activeTab === "readme" ? <ReadmePreview repoId={repoId} /> : null}
              {activeTab === "security" ? (
                <div className="space-y-4">
                  <AgentStatusPanel activeAgents={["security"]} currentStep="Security review ready." />
                  <ChatWindow
                    repoId={repoId}
                    suggestedQuestions={[
                      "Run a security review for this repository.",
                      "Where could secrets or injection risks appear?",
                      "Which files should be reviewed for auth issues?",
                    ]}
                  />
                </div>
              ) : null}
              {activeTab === "files" ? (
                <div className="space-y-4">
                  {priorityFiles.length ? (
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {priorityFiles.map((file, index) => (
                        <motion.button
                          key={file.file_path}
                          type="button"
                          className="rounded-lg border bg-card p-4 text-left shadow-sm transition-colors hover:bg-muted"
                          onClick={() => setSelectedPath(file.file_path)}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.04 }}
                        >
                          <FileCode2 className="h-4 w-4 text-primary" aria-hidden="true" />
                          <div className="mt-3 truncate text-sm font-medium">{file.file_path}</div>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {file.language || "Code"} · {file.chunk_count} chunks
                          </div>
                        </motion.button>
                      ))}
                    </div>
                  ) : null}

                  <Card className="shadow-sm">
                    <CardContent className="p-0">
                      <div className="grid divide-y">
                        {files.map((file) => (
                          <button
                            key={file.file_path}
                            type="button"
                            className={cn(
                              "grid grid-cols-[minmax(0,1fr)_120px_90px] gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-muted",
                              selectedPath === file.file_path && "bg-accent",
                            )}
                            onClick={() => setSelectedPath(file.file_path)}
                          >
                            <span className="truncate font-medium">{file.file_path}</span>
                            <span className="text-muted-foreground">{file.language}</span>
                            <span className="text-right text-muted-foreground">{file.chunk_count} chunks</span>
                          </button>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : null}
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
    </motion.div>
  );
}

function Meta({ icon: Icon, label, value }: { icon: typeof FileStack; label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-3 py-2">
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </dt>
      <dd className="mt-1 truncate font-medium">{value}</dd>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isReady = status === "ready";
  const isFailed = status === "failed";
  return (
    <Badge
      className={cn(
        "gap-1.5 capitalize",
        isReady && "border-emerald-200 bg-emerald-50 text-emerald-700 ring-emerald-200 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
        isFailed && "border-red-200 bg-red-50 text-red-700 ring-red-200 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
        !isReady && !isFailed && "bg-secondary/15 text-secondary-foreground ring-secondary/25",
      )}
    >
      {isReady ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : null}
      {status}
    </Badge>
  );
}

function summarizeLanguages(files: Array<{ language: string }>) {
  const counts = files.reduce<Record<string, number>>((acc, file) => {
    const language = file.language || "Other";
    acc[language] = (acc[language] ?? 0) + 1;
    return acc;
  }, {});
  const total = files.length || 1;
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([language, count]) => ({
      language,
      count,
      percent: Math.max(8, Math.round((count / total) * 100)),
    }));
}

function analysisCompletion(status: string, fileCount: number, chunkCount: unknown): number {
  if (status === "ready") {
    return 100;
  }
  if (status === "failed") {
    return 28;
  }
  if (typeof chunkCount === "number" && chunkCount > 0) {
    return 82;
  }
  if (fileCount > 0) {
    return 56;
  }
  return status === "indexing" ? 24 : 12;
}

function analysisStages(status: string, fileCount: number, chunkCount: unknown) {
  const chunksReady = typeof chunkCount === "number" && chunkCount > 0;
  const ready = status === "ready";
  return [
    {
      label: "Repository cloned",
      detail: fileCount > 0 ? `${fileCount} files discovered` : "Waiting for source files",
      state: fileCount > 0 || ready ? "done" : status === "indexing" ? "active" : "idle",
    },
    {
      label: "Code chunked",
      detail: chunksReady ? `${chunkCount} searchable chunks` : "Preparing context windows",
      state: chunksReady || ready ? "done" : fileCount > 0 ? "active" : "idle",
    },
    {
      label: "Agents primed",
      detail: "Chat, security, README, and review agents",
      state: ready ? "done" : chunksReady ? "active" : "idle",
    },
    {
      label: "Demo ready",
      detail: ready ? "Ask grounded questions now" : "Finalizing index",
      state: ready ? "done" : chunksReady ? "active" : "idle",
    },
  ];
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
