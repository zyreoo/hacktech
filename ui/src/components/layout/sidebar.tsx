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
    <aside className="flex h-full w-60 flex-col border-r border-slate-200 bg-slate-950 dark:border-slate-800">
      {/* Logo / wordmark */}
      <div className="flex h-14 items-center gap-2 border-b border-slate-800 px-5">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500 text-white">
          <Plane className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-bold leading-none text-white">AirHub</p>
          <p className="text-[10px] text-slate-400">Operations Platform</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-0.5 px-3">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-sky-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                  {active && <ChevronRight className="ml-auto h-3 w-3 opacity-60" />}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-800 px-5 py-3">
        <p className="text-[10px] text-slate-500">Airport Data Hub v0.1</p>
      </div>
    </aside>
  );
}
