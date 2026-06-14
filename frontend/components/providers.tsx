"use client";

import { ClerkProvider, useAuth } from "@clerk/nextjs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { ReactNode, useEffect, useState } from "react";
import { Toaster } from "react-hot-toast";

import { setAuthTokenProvider } from "@/lib/api";

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );

  const shell = (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        {publishableKey ? <AuthTokenBridge /> : null}
        {children}
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      </QueryClientProvider>
    </ThemeProvider>
  );

  if (!publishableKey) {
    return shell;
  }

  return <ClerkProvider publishableKey={publishableKey}>{shell}</ClerkProvider>;
}

function AuthTokenBridge() {
  const { getToken } = useAuth();

  useEffect(() => {
    setAuthTokenProvider(() => getToken());
    return () => setAuthTokenProvider(null);
  }, [getToken]);

  return null;
}
