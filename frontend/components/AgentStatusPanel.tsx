"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, RefreshCw } from "lucide-react";

import { getAgentStatus, getAgentTaskStatus } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type AgentName = "Retrieval" | "Code Analysis" | "Security" | "Test Gen" | "README Writer" | "Reviewer";
type AgentState = "idle" | "running" | "done";

type AgentStatusPanelProps = {
  taskId?: string | null;
  activeAgents?: string[];
  completedSteps?: string[];
  currentStep?: string | null;
  loading?: boolean;
  className?: string;
};

const AGENTS: AgentName[] = ["Retrieval", "Code Analysis", "Security", "Test Gen", "README Writer", "Reviewer"];

const STEP_TO_AGENT: Record<string, AgentName> = {
  retrieval: "Retrieval",
  retrieve: "Retrieval",
  code_analysis: "Code Analysis",
  analysis: "Code Analysis",
  security: "Security",
  tests: "Test Gen",
  test_generation: "Test Gen",
  readme: "README Writer",
  readme_crew: "README Writer",
  review: "Reviewer",
  reviewer: "Reviewer",
};

export function AgentStatusPanel({
  taskId,
  activeAgents = [],
  completedSteps = [],
  currentStep,
  loading = false,
  className,
}: AgentStatusPanelProps) {
  const agentsQuery = useQuery({
    queryKey: ["agent-status"],
    queryFn: getAgentStatus,
    enabled: !taskId,
    staleTime: 30_000,
  });

  const taskQuery = useQuery({
    queryKey: ["agent-task-status", taskId],
    queryFn: () => getAgentTaskStatus(taskId ?? ""),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 1500;
    },
  });

  const taskProgress = taskQuery.data;
  const resolvedCurrentStep = currentStep ?? taskProgress?.current_step ?? taskProgress?.current_agent ?? "";
  const resolvedCompleted = taskProgress?.completed_steps ?? completedSteps;
  const statusByAgent = useMemo(() => {
    return AGENTS.reduce<Record<AgentName, AgentState>>((acc, agent) => {
      const normalizedAgent = normalize(agent);
      const isDone = resolvedCompleted.some((step) => stepMatchesAgent(step, agent));
      const isRunning =
        loading ||
        activeAgents.some((active) => normalize(active).includes(normalizedAgent)) ||
        stepMatchesAgent(resolvedCurrentStep, agent);

      acc[agent] = isDone ? "done" : isRunning ? "running" : "idle";
      return acc;
    }, {} as Record<AgentName, AgentState>);
  }, [activeAgents, loading, resolvedCompleted, resolvedCurrentStep]);

  return (
    <aside className={cn("rounded-lg border bg-card p-5", className)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 className="text-base font-semibold">Agents</h2>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => {
            if (taskId) {
              void taskQuery.refetch();
            } else {
              void agentsQuery.refetch();
            }
          }}
          aria-label="Refresh agents"
        >
          <RefreshCw
            className={agentsQuery.isFetching || taskQuery.isFetching ? "h-4 w-4 animate-spin" : "h-4 w-4"}
            aria-hidden="true"
          />
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <AnimatePresence initial={false}>
          {AGENTS.map((agent) => {
            const state = statusByAgent[agent];
            return (
              <motion.div
                key={agent}
                layout
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.96 }}
              >
                <Badge className={cn("gap-1.5", stateClass(state))}>
                  <span className={cn("h-1.5 w-1.5 rounded-full", dotClass(state))} />
                  {agent}
                </Badge>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <p className="mt-4 text-sm text-muted-foreground">
        {taskProgress?.message ?? currentStep ?? globalStatusText(agentsQuery.data?.agents.length ?? 0)}
      </p>
    </aside>
  );
}

function stepMatchesAgent(step: string | null | undefined, agent: AgentName): boolean {
  if (!step) {
    return false;
  }
  const mapped = STEP_TO_AGENT[normalize(step)];
  return mapped === agent || normalize(step).includes(normalize(agent));
}

function normalize(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function stateClass(state: AgentState): string {
  if (state === "done") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200";
  }
  if (state === "running") {
    return "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-200";
  }
  return "border-border bg-muted text-muted-foreground";
}

function dotClass(state: AgentState): string {
  if (state === "done") {
    return "bg-emerald-500";
  }
  if (state === "running") {
    return "animate-pulse bg-blue-500";
  }
  return "bg-muted-foreground";
}

function globalStatusText(count: number): string {
  return count > 0 ? `${count} configured agents are idle.` : "Agent roster ready.";
}
