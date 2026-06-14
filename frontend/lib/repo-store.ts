"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type AnalysedRepo = {
  repo_id: string;
  url: string;
  indexed_at: string;
  task_id?: string;
  status?: "queued" | "ready" | "indexing" | "failed";
  file_count?: number;
};

type RepoStore = {
  repos: AnalysedRepo[];
  upsertRepo: (repo: AnalysedRepo) => void;
  removeRepo: (repoId: string) => void;
};

export const useRepoStore = create<RepoStore>()(
  persist(
    (set) => ({
      repos: [],
      upsertRepo: (repo) =>
        set((state) => {
          const others = state.repos.filter((item) => item.repo_id !== repo.repo_id);
          return { repos: [repo, ...others].slice(0, 20) };
        }),
      removeRepo: (repoId) =>
        set((state) => ({
          repos: state.repos.filter((repo) => repo.repo_id !== repoId),
        })),
    }),
    {
      name: "ai-code-intel-repos",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
