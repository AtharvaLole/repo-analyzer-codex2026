"use client";

import dynamic from "next/dynamic";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Check, Copy, Loader2, SendHorizontal } from "lucide-react";

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
      await revealAssistantMessage(assistantId, response.answer);
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

  async function revealAssistantMessage(messageId: string, answer: string) {
    let visible = "";
    for (const character of answer) {
      visible += character;
      setMessages((current) =>
        current.map((item) => (item.id === messageId ? { ...item, content: visible } : item)),
      );
      await wait(3);
    }
  }

  async function copyAnswer(item: ThreadMessage) {
    await navigator.clipboard.writeText(item.content);
    setCopiedId(item.id);
    window.setTimeout(() => setCopiedId(null), 1200);
  }

  return (
    <div className="rounded-lg border bg-card">
      <div className="min-h-[520px] space-y-5 p-4">
        {messages.length === 0 ? (
          <div className="flex min-h-[360px] flex-col items-center justify-center gap-4 text-center">
            <p className="text-sm text-muted-foreground">Ask a codebase question.</p>
            {suggestedQuestions.length ? (
              <div className="flex flex-wrap justify-center gap-2">
                {suggestedQuestions.map((question) => (
                  <Button key={question} type="button" variant="outline" size="sm" onClick={() => void sendQuestion(question)}>
                    {question}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          messages.map((item) => (
            <article key={item.id} className={item.role === "user" ? "ml-auto max-w-3xl text-right" : "max-w-3xl"}>
              {item.role === "user" ? (
                <div className="inline-block rounded-lg bg-primary px-4 py-3 text-left text-sm text-primary-foreground">
                  <p className="whitespace-pre-wrap">{item.content}</p>
                </div>
              ) : (
                <div className="rounded-lg border bg-muted px-4 py-3 text-sm text-foreground">
                  <div className="flex items-start justify-between gap-3">
                    <ConfidenceBadge confidence={item.confidence ?? 0} />
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
                  <div data-color-mode="light" className="mt-3">
                    {item.content ? <MarkdownPreview source={item.content} /> : <TypingDots />}
                  </div>
                  {item.citations?.length ? (
                    <details className="mt-4 rounded-md border bg-background p-3">
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
          <AgentStatusPanel
            loading
            activeAgents={["retrieval", "code_analysis", "review"]}
            currentStep="Retrieving and analysing code..."
          />
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={onSubmit} className="border-t p-4">
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
          <Textarea
            value={message}
            placeholder="Ask about architecture, tests, security, or implementation details"
            onChange={(event) => setMessage(event.target.value)}
          />
          <Button type="submit" disabled={isLoading || !message.trim()}>
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

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
