import type { SourceCitation } from "@/lib/types";

export function citationSnippet(citation: SourceCitation): string | null | undefined {
  return "snippet" in citation ? citation.snippet : citation.text;
}

export function citationRelevance(citation: SourceCitation): string | undefined {
  return "relevance" in citation ? citation.relevance : undefined;
}

export function citationLabel(citation: SourceCitation): string {
  const fileName = citation.file_path.split("/").pop() ?? citation.file_path;
  return `${fileName}:${citation.start_line}-${citation.end_line}`;
}

export function languageFromPath(filePath: string): string {
  if (filePath.endsWith(".py")) return "python";
  if (filePath.endsWith(".tsx") || filePath.endsWith(".ts")) return "typescript";
  if (filePath.endsWith(".jsx") || filePath.endsWith(".js")) return "javascript";
  if (filePath.endsWith(".go")) return "go";
  if (filePath.endsWith(".rs")) return "rust";
  if (filePath.endsWith(".java")) return "java";
  if (filePath.endsWith(".rb")) return "ruby";
  if (filePath.endsWith(".cpp") || filePath.endsWith(".c") || filePath.endsWith(".h")) return "cpp";
  if (filePath.endsWith(".json")) return "json";
  if (filePath.endsWith(".md")) return "markdown";
  return "text";
}

export function languageTone(filePath: string): string {
  const language = languageFromPath(filePath);
  const tones: Record<string, string> = {
    python: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200",
    javascript:
      "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950 dark:text-yellow-200",
    typescript:
      "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-200",
    go: "border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-200",
    rust: "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-900 dark:bg-orange-950 dark:text-orange-200",
    java: "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
    ruby: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200",
    markdown:
      "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-200",
  };
  return tones[language] ?? "border-border bg-muted text-muted-foreground";
}
