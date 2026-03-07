"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Plane,
  Bell,
  BrainCircuit,
  Wind,
  Layers,
  Users,
  Cpu,
  ShoppingBag,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/modern-ui/scroll-area";

const navItems = [
  { href: "/",               label: "Dashboard",      icon: LayoutDashboard },
  { href: "/flights",        label: "Flights / AODB", icon: Plane },
  { href: "/alerts",         label: "Alerts",         icon: Bell },
  { href: "/predictions",    label: "Predictions",    icon: BrainCircuit },
  { href: "/runways",        label: "Runways",        icon: Wind },
  { href: "/resources",      label: "Resources",      icon: Layers },
  { href: "/passenger-flow", label: "Passenger Flow", icon: Users },
  { href: "/infrastructure", label: "Infrastructure", icon: Cpu },
  { href: "/services",       label: "Services",       icon: ShoppingBag },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-card">
      {/* Logo / wordmark */}
      <div className="flex h-16 items-center gap-3 border-b px-6">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
          <Plane className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-bold leading-none">AirHub</p>
          <p className="text-[11px] text-muted-foreground">Operations Platform</p>
        </div>
      </div>

      {/* Nav */}
      <ScrollArea className="flex-1 py-4">
        <nav className="px-3">
          <ul className="space-y-1">
            {navItems.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={cn(
                      "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                  >
                    <Icon className={cn("h-4 w-4 shrink-0", active ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
                    {label}
                    {active && <ChevronRight className="ml-auto h-4 w-4 text-primary opacity-70" />}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t px-5 py-4">
        <p className="text-[11px] text-muted-foreground">Airport Data Hub v0.1</p>
      </div>
    </aside>
  );
}
