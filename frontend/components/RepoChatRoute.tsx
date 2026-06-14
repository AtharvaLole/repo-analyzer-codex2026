"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { ChatWindow } from "@/components/ChatWindow";
import { Badge } from "@/components/ui/badge";
import { getChatHistory, getRepositoryFiles } from "@/lib/api";
import { repoTypeLabel, suggestedQuestionsForFiles } from "@/lib/repo-insights";

type RepoChatRouteProps = {
  repoId: string;
};

export function RepoChatRoute({ repoId }: RepoChatRouteProps) {
  const filesQuery = useQuery({
    queryKey: ["repo-files", repoId],
    queryFn: () => getRepositoryFiles(repoId),
  });
  const historyQuery = useQuery({
    queryKey: ["chat-history", repoId],
    queryFn: () => getChatHistory(repoId),
  });

  const files = filesQuery.data?.files ?? [];
  const suggestions = useMemo(() => suggestedQuestionsForFiles(files), [files]);
  const repoType = repoTypeLabel(files);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Badge>{repoType}</Badge>
            <p className="text-xs font-semibold uppercase text-primary">Repository chat</p>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-normal">{repoId}</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          {historyQuery.data?.history.length ?? 0} saved Q&A pairs
        </p>
      </div>
      <ChatWindow
        repoId={repoId}
        initialHistory={historyQuery.data?.history ?? []}
        suggestedQuestions={suggestions}
      />
    </div>
  );
}
