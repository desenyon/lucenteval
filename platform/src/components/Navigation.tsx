"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/prompts", label: "Prompts" },
  { href: "/docs", label: "Docs" },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav
      className="sticky top-0 z-50"
      style={{
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(40px)",
        WebkitBackdropFilter: "blur(40px)",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <div className="max-w-7xl mx-auto px-5 md:px-8">
        <div className="flex h-14 items-center justify-between gap-6">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
            <div
              className="w-6 h-6 rounded-lg flex items-center justify-center"
              style={{
                background: "linear-gradient(135deg, #00E5FF 0%, #0066FF 100%)",
                boxShadow: "0 0 16px rgba(0,102,255,0.5)",
              }}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 1L10.5 10H1.5L6 1Z" fill="white" fillOpacity="0.95" />
              </svg>
            </div>
            <span
              className="text-sm font-semibold tracking-tight"
              style={{ color: "rgba(255,255,255,0.92)", letterSpacing: "-0.02em" }}
            >
              Lucent Eval
            </span>
          </Link>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-0.5">
            {links.map((link) => {
              const active = pathname === link.href || pathname.startsWith(link.href + "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
                  style={{
                    color: active ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.45)",
                    background: active ? "rgba(255,255,255,0.08)" : "transparent",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Link href="/dashboard/settings" className="btn-secondary" style={{ fontSize: "12px", padding: "7px 14px" }}>
              Settings
            </Link>
            <Link href="/dashboard/runs/new" className="btn-primary" style={{ fontSize: "12px", padding: "7px 14px" }}>
              + New Run
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
