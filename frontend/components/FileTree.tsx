"use client";

import { ChevronRight, FileCode2, Folder } from "lucide-react";

import type { RepoFileInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

type FileTreeProps = {
  files: RepoFileInfo[];
  selectedPath?: string;
  onSelect?: (filePath: string) => void;
  maxItems?: number;
};

type TreeNode = {
  name: string;
  path: string;
  children: Map<string, TreeNode>;
  file?: RepoFileInfo;
};

export function FileTree({ files, selectedPath, onSelect, maxItems = 160 }: FileTreeProps) {
  const root = buildTree(files.slice(0, maxItems));

  if (!files.length) {
    return <p className="text-sm text-muted-foreground">No indexed files found.</p>;
  }

  return (
    <div className="space-y-1 text-sm">
      {Array.from(root.children.values()).map((node) => (
        <TreeBranch key={node.path} node={node} selectedPath={selectedPath} onSelect={onSelect} depth={0} />
      ))}
      {files.length > maxItems ? (
        <p className="px-2 pt-2 text-xs text-muted-foreground">Showing first {maxItems} indexed files.</p>
      ) : null}
    </div>
  );
}

function TreeBranch({
  node,
  selectedPath,
  onSelect,
  depth,
}: {
  node: TreeNode;
  selectedPath?: string;
  onSelect?: (filePath: string) => void;
  depth: number;
}) {
  const isFile = Boolean(node.file);
  const isSelected = selectedPath === node.path;

  if (isFile) {
    return (
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-muted",
          isSelected && "bg-accent text-accent-foreground",
        )}
        style={{ paddingLeft: `${8 + depth * 14}px` }}
        onClick={() => onSelect?.(node.path)}
      >
        <FileCode2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-muted-foreground" style={{ paddingLeft: `${8 + depth * 14}px` }}>
        <ChevronRight className="h-3 w-3" aria-hidden="true" />
        <Folder className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="truncate">{node.name}</span>
      </div>
      {Array.from(node.children.values()).map((child) => (
        <TreeBranch key={child.path} node={child} selectedPath={selectedPath} onSelect={onSelect} depth={depth + 1} />
      ))}
    </div>
  );
}

function buildTree(files: RepoFileInfo[]): TreeNode {
  const root: TreeNode = { name: "", path: "", children: new Map() };

  for (const file of files) {
    const parts = file.file_path.split("/").filter(Boolean);
    let current = root;
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      const isLeaf = index === parts.length - 1;
      if (!current.children.has(part)) {
        current.children.set(part, { name: part, path, children: new Map() });
      }
      const next = current.children.get(part);
      if (!next) {
        return;
      }
      if (isLeaf) {
        next.file = file;
      }
      current = next;
    });
  }

  return root;
}
