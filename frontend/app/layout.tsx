import type { Metadata } from "next";
import Link from "next/link";
import { Code2 } from "lucide-react";

import { AuthControls } from "@/components/AuthControls";
import { Providers } from "@/components/providers";
import { ThemeToggle } from "@/components/ThemeToggle";

import "@uiw/react-md-editor/markdown-editor.css";
import "@uiw/react-markdown-preview/markdown.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Powered Code Intelligence",
  description: "Repository analysis, chat, README generation, and agent status.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="min-h-screen bg-background text-foreground">
            <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
              <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
                <Link href="/" className="flex items-center gap-2 text-sm font-semibold">
                  <Code2 className="h-5 w-5 text-primary" aria-hidden="true" />
                  <span>Code Intelligence</span>
                </Link>
                <div className="flex items-center gap-2">
                  <Link href="/dashboard" className="hidden text-sm font-medium text-muted-foreground sm:inline">
                    Dashboard
                  </Link>
                  <ThemeToggle />
                  <AuthControls />
                </div>
              </div>
            </header>
            <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
