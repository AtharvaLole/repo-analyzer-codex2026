"use client";

import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { CalendarDays, FileCode2, MessageSquareText, RefreshCw, Trash2 } from "lucide-react";

import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { AuthGate } from "@/components/AuthGate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getRepositoryFiles, getRepositoryStatus } from "@/lib/api";
import { useRepoStore } from "@/lib/repo-store";

export default function DashboardPage() {
  return (
    <AuthGate>
      <DashboardContent />
    </AuthGate>
  );
}

function DashboardContent() {
  const repos = useRepoStore((state) => state.repos);
  const removeRepo = useRepoStore((state) => state.removeRepo);

  const statusQueries = useQueries({
    queries: repos.map((repo) => ({
      queryKey: ["repo-status", repo.repo_id],
      queryFn: () => getRepositoryStatus(repo.repo_id),
      refetchInterval: repo.status === "queued" || repo.status === "indexing" ? 5000 : (false as const),
    })),
  });

  const fileQueries = useQueries({
    queries: repos.map((repo) => ({
      queryKey: ["repo-files", repo.repo_id],
      queryFn: () => getRepositoryFiles(repo.repo_id),
      enabled: statusQueries[repos.findIndex((item) => item.repo_id === repo.repo_id)]?.data?.status === "ready",
      staleTime: 60_000,
    })),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Repository Dashboard</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Previously analysed repositories from this browser, refreshed against the API.
          </p>
        </div>

        {repos.length === 0 ? (
          <Card>
            <CardContent className="flex min-h-72 flex-col items-center justify-center p-8 text-center">
              <FileCode2 className="h-8 w-8 text-primary" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold">No repositories yet</h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                Analyse a GitHub repository from the home page and it will appear here.
              </p>
              <Button asChild className="mt-5">
                <Link href="/">Analyse Repository</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {repos.map((repo, index) => {
              const status = statusQueries[index]?.data;
              const files = fileQueries[index]?.data;
              const fileCount = status?.meta?.file_count ?? repo.file_count ?? files?.files.length ?? 0;
              const indexedAt = status?.meta?.indexed_at ?? repo.indexed_at;
              const displayStatus = status?.status ?? repo.status ?? "indexing";

              return (
                <Card key={repo.repo_id}>
                  <CardContent className="p-5">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="truncate text-base font-semibold">{repo.url}</h2>
                          <Badge>{displayStatus}</Badge>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                          <span className="inline-flex items-center gap-2">
                            <CalendarDays className="h-4 w-4" aria-hidden="true" />
                            {formatDate(indexedAt)}
                          </span>
                          <span className="inline-flex items-center gap-2">
                            <FileCode2 className="h-4 w-4" aria-hidden="true" />
                            {fileCount} files
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/repo/${encodeURIComponent(repo.repo_id)}`}>
                            <RefreshCw className="h-4 w-4" aria-hidden="true" />
                            Overview
                          </Link>
                        </Button>
                        <Button asChild size="sm">
                          <Link href={`/repo/${encodeURIComponent(repo.repo_id)}/chat`}>
                            <MessageSquareText className="h-4 w-4" aria-hidden="true" />
                            Chat
                          </Link>
                        </Button>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          aria-label={`Remove ${repo.url}`}
                          onClick={() => removeRepo(repo.repo_id)}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <AgentStatusPanel />
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}
