"use client";

import { Bell, RefreshCw } from "lucide-react";
import { Button } from "@/components/modern-ui/button";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const queryClient = useQueryClient();
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = async () => {
    setSpinning(true);
    await queryClient.invalidateQueries();
    setTimeout(() => setSpinning(false), 600);
  };

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-card px-6">
      <div>
        <h1 className="text-base font-semibold text-foreground">{title}</h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="icon" onClick={handleRefresh} title="Refresh all data">
          <RefreshCw className={cn("h-4 w-4 text-muted-foreground", spinning && "animate-spin")} />
        </Button>
        <Button variant="ghost" size="icon" title="Alerts">
          <Bell className="h-4 w-4 text-muted-foreground" />
        </Button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">
          OP
        </div>
      </div>
    </header>
  );
}
