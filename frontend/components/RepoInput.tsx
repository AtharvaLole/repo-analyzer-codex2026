"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, GitBranch, Loader2 } from "lucide-react";

import { getAgentTaskStatus, indexRepository } from "@/lib/api";
import { useRepoStore } from "@/lib/repo-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const STEP_COPY: Record<string, string> = {
  queued: "Queued...",
  clone: "Cloning...",
  chunk: "Parsing files...",
  embed: "Embedding...",
  metadata: "Done!",
  complete: "Done!",
};

export function RepoInput() {
  const router = useRouter();
  const upsertRepo = useRepoStore((state) => state.upsertRepo);
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [repoId, setRepoId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const progressQuery = useQuery({
    queryKey: ["task-progress", taskId],
    queryFn: () => getAgentTaskStatus(taskId ?? ""),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 1500;
    },
  });

  const mutation = useMutation({
    mutationFn: () => indexRepository({ github_url: repositoryUrl.trim() }),
    onSuccess: (result) => {
      setTaskId(result.task_id || null);
      setRepoId(result.repo_id);
      upsertRepo({
        repo_id: result.repo_id,
        url: repositoryUrl.trim(),
        indexed_at: new Date().toISOString(),
        task_id: result.task_id,
        status: result.status,
        file_count: result.result?.total_files,
      });
      if (result.status === "ready") {
        router.push(`/repo/${encodeURIComponent(result.repo_id)}`);
      }
    },
    onError: (caught) => {
      const message = caught instanceof Error ? caught.message : "Repository indexing could not be queued.";
      setError(message);
    },
  });

  const progress = progressQuery.data?.progress ?? progressQuery.data?.percent ?? (mutation.isPending ? 8 : 0);
  const currentStep = progressQuery.data?.current_step ?? (mutation.isPending ? "queued" : "");
  const stepText = progressQuery.data?.message ?? STEP_COPY[currentStep] ?? "Waiting...";
  const isDone = progressQuery.data?.status === "ready";
  const isFailed = progressQuery.data?.status === "failed";

  const validationError = useMemo(() => {
    if (!repositoryUrl.trim()) {
      return null;
    }
    return isGithubUrl(repositoryUrl.trim()) ? null : "Enter a valid GitHub repository URL.";
  }, [repositoryUrl]);

  useEffect(() => {
    if (!isDone || !repoId) {
      return;
    }
    const timeout = window.setTimeout(() => {
      router.push(`/repo/${encodeURIComponent(repoId)}`);
    }, 700);
    return () => window.clearTimeout(timeout);
  }, [isDone, repoId, router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!isGithubUrl(repositoryUrl.trim())) {
      setError("Enter a valid GitHub repository URL.");
      return;
    }

    mutation.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="rounded-lg border bg-card p-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
        <label className="grid gap-2">
          <span className="text-sm font-medium">Repository URL</span>
          <Input
            required
            type="url"
            value={repositoryUrl}
            placeholder="https://github.com/org/repo"
            aria-invalid={Boolean(validationError || error)}
            onChange={(event) => setRepositoryUrl(event.target.value)}
          />
        </label>
        <div className="flex items-end">
          <Button type="submit" disabled={mutation.isPending || Boolean(validationError)} className="w-full lg:w-auto">
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : isDone ? (
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            ) : (
              <GitBranch className="h-4 w-4" aria-hidden="true" />
            )}
            Analyse
          </Button>
        </div>
      </div>

      {taskId ? (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{isDone ? "Done!" : isFailed ? "Indexing failed" : stepText}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full transition-all", isFailed ? "bg-destructive" : "bg-primary")}
              style={{ width: `${Math.max(4, Math.min(100, progress))}%` }}
            />
          </div>
          <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground">
            {["clone", "chunk", "embed", "metadata"].map((step) => (
              <span key={step} className={progress >= stepPercent(step) ? "text-primary" : ""}>
                {STEP_COPY[step]}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {validationError ? <p className="mt-3 text-sm text-destructive">{validationError}</p> : null}
      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      {isFailed && progressQuery.data?.message ? (
        <p className="mt-3 text-sm text-destructive">{progressQuery.data.message}</p>
      ) : null}
    </form>
  );
}

function isGithubUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.hostname === "github.com" && url.pathname.split("/").filter(Boolean).length >= 2;
  } catch {
    return false;
  }
}

function stepPercent(step: string): number {
  const values: Record<string, number> = {
    clone: 10,
    chunk: 40,
    embed: 80,
    metadata: 100,
  };
  return values[step] ?? 0;
}
