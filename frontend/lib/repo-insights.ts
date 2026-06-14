import type { RepoFileInfo } from "@/lib/types";

export function suggestedQuestionsForFiles(files: RepoFileInfo[]): string[] {
  const paths = files.map((file) => file.file_path.toLowerCase());
  const hasPython = paths.some((path) => path.endsWith(".py"));
  const hasNext = paths.some((path) => path.includes("app/") && (path.endsWith(".tsx") || path.endsWith(".ts")));
  const hasFastApi = paths.some((path) => path.includes("main.py") || path.includes("api/"));
  const hasPackageJson = paths.some((path) => path.endsWith("package.json"));
  const hasDocker = paths.some((path) => path.includes("dockerfile") || path.includes("docker-compose"));

  const questions = [
    "What are the main entry points?",
    "Explain the request lifecycle.",
    "Where are the highest-risk security areas?",
  ];

  if (hasFastApi) {
    questions.push("How are the FastAPI routes organized?");
  }
  if (hasNext) {
    questions.push("How is the Next.js app structured?");
  }
  if (hasPython) {
    questions.push("Which Python modules need tests first?");
  }
  if (hasPackageJson || hasDocker) {
    questions.push("How do I run this project locally?");
  }

  return questions.slice(0, 6);
}

export function repoTypeLabel(files: RepoFileInfo[]): string {
  const paths = files.map((file) => file.file_path.toLowerCase());
  if (paths.some((path) => path.endsWith("next.config.js") || path.endsWith("next.config.mjs"))) {
    return "Next.js";
  }
  if (paths.some((path) => path.includes("fastapi") || path.endsWith("main.py"))) {
    return "FastAPI";
  }
  if (paths.some((path) => path.endsWith("package.json"))) {
    return "JavaScript";
  }
  if (paths.some((path) => path.endsWith("pyproject.toml") || path.endsWith("requirements.txt"))) {
    return "Python";
  }
  return "Repository";
}
