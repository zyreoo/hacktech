import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Sidebar } from "@/components/layout/sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Airport Data Hub",
  description: "Airport Operations Control Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body
        className={`${geistSans.variable} ${geistMono.variable} h-full bg-slate-50 font-sans antialiased dark:bg-slate-950`}
      >
        <QueryProvider>
          <TooltipProvider>
            <div className="flex h-full">
              <Sidebar />
              <div className="flex min-h-full flex-1 flex-col overflow-hidden">
                {children}
              </div>
            </div>
          </TooltipProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
