"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Download, FileText, Loader2, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";

import { generateReadme, getAgentTaskStatus, getReadme } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MarkdownPreview = dynamic(() => import("@uiw/react-md-editor").then((module) => module.default.Markdown), {
  ssr: false,
});

type ReadmePreviewProps = {
  repoId: string;
};

export function ReadmePreview({ repoId }: ReadmePreviewProps) {
  const [markdown, setMarkdown] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const readmeQuery = useQuery({
    queryKey: ["readme", repoId],
    queryFn: () => getReadme(repoId),
    retry: false,
  });

  const progressQuery = useQuery({
    queryKey: ["readme-task", taskId],
    queryFn: () => getAgentTaskStatus(taskId ?? ""),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 1500;
    },
  });

  const generateMutation = useMutation({
    mutationFn: (forceRegenerate: boolean) => generateReadme({ repo_id: repoId, force_regenerate: forceRegenerate }),
    onSuccess: (result) => {
      setTaskId(result.task_id);
      toast.success("README generation queued.");
    },
  });

  useEffect(() => {
    if (readmeQuery.data?.content || readmeQuery.data?.markdown) {
      setMarkdown(readmeQuery.data.content ?? readmeQuery.data.markdown ?? "");
    }
  }, [readmeQuery.data]);

  useEffect(() => {
    if (progressQuery.data?.status === "ready") {
      void readmeQuery.refetch();
    }
  }, [progressQuery.data?.status, readmeQuery]);

  const confidence = readmeQuery.data?.confidence ?? 0;
  const hasReadme = Boolean(readmeQuery.data?.content || readmeQuery.data?.markdown);
  const progress = progressQuery.data?.progress ?? 0;
  const progressMessage = progressQuery.data?.message ?? "Waiting for README generation.";

  const renderedMarkdown = useMemo(
    () => markdown || "# README\n\nGenerate a draft to preview it here.",
    [markdown],
  );

  async function copyMarkdown() {
    await navigator.clipboard.writeText(renderedMarkdown);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  function downloadMarkdown() {
    const blob = new Blob([renderedMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "README.md";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-4">
        <div>
          <h2 className="text-base font-semibold">README Preview</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasReadme ? "Edit or export the generated markdown." : "Generate a README to populate the preview."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ConfidenceBadge confidence={confidence} />
          <Button type="button" variant="outline" onClick={() => void copyMarkdown()}>
            {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <FileText className="h-4 w-4" aria-hidden="true" />}
            Copy
          </Button>
          <Button type="button" variant="outline" onClick={downloadMarkdown}>
            <Download className="h-4 w-4" aria-hidden="true" />
            Download
          </Button>
          <Button
            type="button"
            onClick={() => generateMutation.mutate(hasReadme)}
            disabled={generateMutation.isPending}
          >
            {generateMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            )}
            {hasReadme ? "Regenerate" : "Generate"}
          </Button>
        </div>
      </div>

      {taskId ? (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{progressMessage}</span>
            <span>{progress}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.max(4, progress)}%` }} />
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border bg-card p-4">
          <div className="mb-3 text-sm font-medium">Raw markdown</div>
          <Textarea
            value={renderedMarkdown}
            onChange={(event) => setMarkdown(event.target.value)}
            className="min-h-[580px] font-mono text-xs leading-5"
          />
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="mb-3 text-sm font-medium">Rendered preview</div>
          <div data-color-mode="light" className="min-h-[580px] overflow-auto rounded-md border bg-background p-4">
            <MarkdownPreview source={renderedMarkdown} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  return (
    <Badge
      className={cn(
        confidence > 80 &&
          "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
        confidence >= 50 &&
          confidence <= 80 &&
          "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-200",
        confidence < 50 &&
          "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
      )}
    >
      Confidence {confidence || "--"}%
    </Badge>
  );
}
