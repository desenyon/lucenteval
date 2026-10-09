import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { Navigation } from "@/components/Navigation";

export const metadata: Metadata = {
  title: "Lucent Eval — AI Agent Adversarial Testing",
  description:
    "Benchmark your AI agents against the bundled adversarial corpus across 6 dimensions. Public leaderboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-oled-base text-white font-sans">
        <Providers>
          <div className="relative z-10 min-h-screen flex flex-col">
            <Navigation />
            <main className="flex-1 max-w-7xl mx-auto w-full px-5 py-8 md:px-8">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
