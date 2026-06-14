"use client";

import dynamic from "next/dynamic";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Check, Copy, Loader2, SendHorizontal, Sparkles } from "lucide-react";

import { askRepositoryQuestion } from "@/lib/api";
import type { ChatHistoryItem, ChatMessage, SourceCitation } from "@/lib/types";
import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { CodeCitation } from "@/components/CodeCitation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MarkdownPreview = dynamic(() => import("@uiw/react-md-editor").then((module) => module.default.Markdown), {
  ssr: false,
});

type ChatWindowProps = {
  repoId: string;
  initialHistory?: ChatHistoryItem[];
  suggestedQuestions?: string[];
};

type ThreadMessage = ChatMessage & {
  id: string;
  citations?: SourceCitation[];
  confidence?: number;
};

export function ChatWindow({ repoId, initialHistory = [], suggestedQuestions = [] }: ChatWindowProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ThreadMessage[]>(() => historyToMessages(initialHistory));
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const initializedHistoryRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (initializedHistoryRef.current || !initialHistory.length || messages.length) {
      return;
    }
    initializedHistoryRef.current = true;
    setMessages(historyToMessages(initialHistory));
  }, [initialHistory, messages.length]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendQuestion(message);
  }

  async function sendQuestion(rawQuestion: string) {
    const trimmed = rawQuestion.trim();
    if (!trimmed || isLoading) {
      return;
    }

    setMessage("");
    setIsLoading(true);
    const userMessage: ThreadMessage = { id: crypto.randomUUID(), role: "user", content: trimmed };
    const assistantId = crypto.randomUUID();
    const nextMessages: ThreadMessage[] = [
      ...messages,
      userMessage,
      { id: assistantId, role: "assistant", content: "", confidence: 0, citations: [] },
    ];
    setMessages(nextMessages);

    try {
      const response = await askRepositoryQuestion({
        repo_id: repoId,
        question: trimmed,
        message: trimmed,
        history: messages.map(({ role, content }) => ({ role, content })),
      });
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? {
                ...item,
                content: response.answer,
                citations: response.citations,
                confidence: response.confidence,
              }
            : item,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function copyAnswer(item: ThreadMessage) {
    await navigator.clipboard.writeText(item.content);
    setCopiedId(item.id);
    window.setTimeout(() => setCopiedId(null), 1200);
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] min-h-[620px] flex-col overflow-hidden rounded-lg border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b bg-muted/35 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Bot className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">Repository Chat</h2>
            <p className="truncate text-xs text-muted-foreground">Grounded answers with file citations</p>
          </div>
        </div>
        <Badge className="hidden shrink-0 gap-1.5 border-border bg-background text-foreground sm:inline-flex">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          Indexed RAG
        </Badge>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <div className="flex min-h-full flex-col items-center justify-center gap-5 text-center">
            <div>
              <h3 className="text-lg font-semibold">Ask about this codebase</h3>
              <p className="mt-1 text-sm text-muted-foreground">Architecture, routes, auth, models, risks, or setup.</p>
            </div>
            {suggestedQuestions.length ? (
              <div className="grid w-full max-w-2xl gap-2 sm:grid-cols-2">
                {suggestedQuestions.map((question) => (
                  <Button
                    key={question}
                    type="button"
                    variant="outline"
                    className="h-auto justify-start whitespace-normal px-3 py-2 text-left text-xs"
                    onClick={() => void sendQuestion(question)}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          messages.map((item) => (
            <article key={item.id} className={item.role === "user" ? "ml-auto max-w-[78%] text-right" : "max-w-[86%]"}>
              {item.role === "user" ? (
                <div className="inline-block rounded-lg bg-primary px-4 py-3 text-left text-sm leading-6 text-primary-foreground shadow-sm">
                  <p className="whitespace-pre-wrap">{item.content}</p>
                </div>
              ) : (
                <div className="rounded-lg border bg-background px-4 py-4 text-sm text-foreground shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-accent-foreground">
                        <Bot className="h-4 w-4" aria-hidden="true" />
                      </div>
                      <ConfidenceBadge confidence={item.confidence ?? 0} />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="Copy answer"
                      onClick={() => void copyAnswer(item)}
                    >
                      {copiedId === item.id ? (
                        <Check className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                      ) : (
                        <Copy className="h-4 w-4" aria-hidden="true" />
                      )}
                    </Button>
                  </div>
                  <div data-color-mode="light" className="prose-chat mt-3">
                    {item.content ? <MarkdownPreview source={item.content} /> : <TypingDots />}
                  </div>
                  {item.citations?.length ? (
                    <details className="mt-4 rounded-md border bg-muted/35 p-3">
                      <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">
                        Citations ({item.citations.length})
                      </summary>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.citations.map((citation) => (
                          <CodeCitation key={`${citation.file_path}-${citation.start_line}-${citation.end_line}`} citation={citation} />
                        ))}
                      </div>
                    </details>
                  ) : null}
                </div>
              )}
            </article>
          ))
        )}

        {isLoading ? (
          <div className="max-w-[86%]">
            <AgentStatusPanel
              loading
              activeAgents={["retrieval", "code_analysis"]}
              currentStep="Retrieving indexed code and preparing citations..."
            />
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t bg-background p-4">
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
          <Textarea
            value={message}
            placeholder="Ask about architecture, tests, security, or implementation details"
            className="min-h-[52px] resize-none"
            onChange={(event) => setMessage(event.target.value)}
          />
          <Button type="submit" className="h-[52px] px-5" disabled={isLoading || !message.trim()}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <SendHorizontal className="h-4 w-4" aria-hidden="true" />
            )}
            Send
          </Button>
        </div>
      </form>
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

function TypingDots() {
  return (
    <span className="inline-flex gap-1 text-muted-foreground">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:120ms]" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:240ms]" />
    </span>
  );
}

function historyToMessages(history: ChatHistoryItem[]): ThreadMessage[] {
  return history.flatMap((item) => [
    { id: crypto.randomUUID(), role: "user", content: item.question },
    {
      id: crypto.randomUUID(),
      role: "assistant",
      content: item.answer,
      citations: item.citations,
      confidence: item.confidence,
    },
  ]);
}
