"use client";

import { useState } from "react";
import { FileCode2, X } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";

import { citationLabel, citationRelevance, citationSnippet, languageFromPath, languageTone } from "@/lib/citations";
import type { SourceCitation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type CodeCitationProps = {
  citation: SourceCitation;
};

export function CodeCitation({ citation }: CodeCitationProps) {
  const [isOpen, setIsOpen] = useState(false);
  const snippet = citationSnippet(citation) ?? "";
  const language = languageFromPath(citation.file_path);

  return (
    <>
      <button
        type="button"
        className={cn(
          "group relative inline-flex max-w-full items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium",
          languageTone(citation.file_path),
        )}
        onClick={() => setIsOpen(true)}
      >
        <FileCode2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span className="truncate">{citationLabel(citation)}</span>
        {snippet ? (
          <span className="pointer-events-none absolute left-0 top-full z-30 mt-2 hidden w-80 rounded-md border bg-popover p-3 text-left text-popover-foreground shadow-lg group-hover:block">
            <span className="mb-2 block text-[11px] font-semibold uppercase text-muted-foreground">{language}</span>
            <code className="line-clamp-6 whitespace-pre-wrap font-mono text-[11px] leading-5">{snippet}</code>
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="max-h-[86vh] w-full max-w-4xl overflow-hidden rounded-lg border bg-card shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b p-4">
              <div className="min-w-0">
                <h2 className="truncate text-base font-semibold">{citation.file_path}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Lines {citation.start_line}-{citation.end_line}
                  {citationRelevance(citation) ? ` · ${citationRelevance(citation)}` : ""}
                </p>
              </div>
              <Button type="button" variant="ghost" size="icon" aria-label="Close citation" onClick={() => setIsOpen(false)}>
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="max-h-[70vh] overflow-auto">
              {snippet ? (
                <SyntaxHighlighter language={language} style={oneDark} showLineNumbers customStyle={{ margin: 0 }}>
                  {snippet}
                </SyntaxHighlighter>
              ) : (
                <p className="p-4 text-sm text-muted-foreground">No snippet was returned for this citation.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
