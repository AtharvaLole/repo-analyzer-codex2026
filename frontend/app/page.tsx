"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BookOpenText, Loader2, SearchCode, ShieldCheck, Sparkles } from "lucide-react";

import { indexRepository } from "@/lib/api";
import { useRepoStore } from "@/lib/repo-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const features = [
  {
    title: "RAG Q&A",
    description: "Ask grounded questions with file and line citations from the indexed repository.",
    icon: SearchCode,
  },
  {
    title: "README Generator",
    description: "Create project documentation from architecture, dependencies, and detected entry points.",
    icon: BookOpenText,
  },
  {
    title: "Security Scan",
    description: "Use static analysis and code review agents to surface risky implementation patterns.",
    icon: ShieldCheck,
  },
];

export default function HomePage() {
  const router = useRouter();
  const upsertRepo = useRepoStore((state) => state.upsertRepo);
  const [githubUrl, setGithubUrl] = useState("");

  const mutation = useMutation({
    mutationFn: () => indexRepository({ github_url: githubUrl.trim() }),
    onSuccess: (result) => {
      upsertRepo({
        repo_id: result.repo_id,
        url: githubUrl.trim(),
        indexed_at: new Date().toISOString(),
        task_id: result.task_id,
        status: result.status,
        file_count: result.result?.total_files,
      });
      router.push(`/repo/${encodeURIComponent(result.repo_id)}`);
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!githubUrl.trim() || mutation.isPending) {
      return;
    }
    mutation.mutate();
  }

  return (
    <div className="space-y-10">
      <section className="grid min-h-[calc(100vh-9rem)] items-center gap-8 py-8 lg:grid-cols-[minmax(0,1fr)_420px]">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-md border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />
            Multi-agent repository analysis
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-normal text-foreground sm:text-5xl lg:text-6xl">
            AI-Powered Code Intelligence
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            Index a GitHub repository, ask implementation questions, generate documentation, and inspect agent output
            from one focused workspace.
          </p>
          <form onSubmit={onSubmit} className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <Input
              required
              type="url"
              value={githubUrl}
              placeholder="https://github.com/org/repo"
              aria-label="GitHub repository URL"
              onChange={(event) => setGithubUrl(event.target.value)}
            />
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <SearchCode className="h-4 w-4" aria-hidden="true" />
              )}
              Analyse Repository
            </Button>
          </form>
        </div>

        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="rounded-md border bg-background p-4 font-mono text-xs leading-6">
            <div className="text-muted-foreground">$ analyse https://github.com/acme/api</div>
            <div className="mt-3 text-primary">clone: ready</div>
            <div className="text-primary">chunk: 1,248 code sections</div>
            <div className="text-secondary">embed: writing ChromaDB index</div>
            <div className="mt-3 text-muted-foreground">agents: retrieval, readme, security, review</div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ delay: index * 0.06, duration: 0.24 }}
            >
              <Card className="h-full">
                <CardContent className="p-5">
                  <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  <h2 className="mt-4 text-base font-semibold">{feature.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </section>
    </div>
  );
}
