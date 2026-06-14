"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpenText, FileCode2, MessageSquareText, ShieldCheck } from "lucide-react";

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

  return (
    <div className="space-y-5">
      <header className="rounded-lg border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{repoType}</Badge>
              <Badge>{statusQuery.data?.status ?? "loading"}</Badge>
            </div>
            <h1 className="mt-3 truncate text-2xl font-semibold tracking-normal">{meta?.url ?? repoId}</h1>
            <p className="mt-2 break-all text-sm text-muted-foreground">Commit {meta?.commit_sha ?? "unknown"}</p>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <Meta label="Files" value={String(meta?.file_count ?? files.length)} />
            <Meta label="Chunks" value={String(meta?.chunk_count ?? "--")} />
            <Meta label="Last indexed" value={formatDate(String(meta?.indexed_at ?? ""))} />
          </dl>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="rounded-lg border bg-card p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">Files</h2>
            <span className="text-xs text-muted-foreground">{files.length}</span>
          </div>
          <div className="max-h-[720px] overflow-auto">
            <FileTree files={files} selectedPath={selectedPath} onSelect={setSelectedPath} />
          </div>
        </aside>

        <section className="min-w-0 space-y-4">
          <div className="flex flex-wrap gap-2 rounded-lg border bg-card p-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <Button
                  key={tab.key}
                  type="button"
                  variant={activeTab === tab.key ? "default" : "ghost"}
                  onClick={() => setActiveTab(tab.key)}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {tab.label}
                </Button>
              );
            })}
          </div>

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
            <Card>
              <CardContent className="p-0">
                <div className="grid divide-y">
                  {files.map((file) => (
                    <button
                      key={file.file_path}
                      type="button"
                      className={cn(
                        "grid grid-cols-[minmax(0,1fr)_120px_90px] gap-3 px-4 py-3 text-left text-sm hover:bg-muted",
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
          ) : null}
        </section>
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-3 py-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium">{value}</dd>
    </div>
  );
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
