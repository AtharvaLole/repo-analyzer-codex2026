"use client";

import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import { LockKeyhole } from "lucide-react";
import { ReactNode } from "react";

import { Button } from "@/components/ui/button";

type AuthGateProps = {
  children: ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const enabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!enabled) {
    return <>{children}</>;
  }

  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <div className="mx-auto flex min-h-[420px] max-w-md flex-col items-center justify-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-md border border-border bg-card">
            <LockKeyhole className="h-5 w-5 text-primary" aria-hidden="true" />
          </div>
          <h1 className="mt-5 text-2xl font-semibold tracking-normal">Sign in to view your dashboard</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Your analysed repositories are synced from this browser and refreshed against the API.
          </p>
          <SignInButton mode="modal">
            <Button type="button" className="mt-5">
              Sign in
            </Button>
          </SignInButton>
        </div>
      </SignedOut>
    </>
  );
}
