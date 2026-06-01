"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearAccessToken, getAccessToken } from "../lib/api";

const links = [
  ["Bookings", "/dashboard"],
  ["Services", "/dashboard/services"],
  ["Staff", "/dashboard/staff"],
  ["Availability", "/dashboard/availability"],
  ["Settings", "/dashboard/settings"],
];

export function DashboardShell({ title, children }: { title: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      clearAccessToken();
      const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
      window.location.replace(`/login?next=${next}`);
      return;
    }
    setIsAuthorized(true);
  }, []);

  if (!isAuthorized) {
    return (
      <main className="page-shell">
        <section className="panel">
          <p className="muted">Checking session...</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="grid gap-5 rounded-xl border border-line/80 bg-white/80 p-4 shadow-sm backdrop-blur sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Business dashboard</p>
            <h1 className="mt-1 text-3xl font-semibold">{title}</h1>
          </div>
          <Link href="/dashboard/settings" className="button">Settings</Link>
        </div>
        <nav className="flex flex-wrap gap-2">
          {links.map(([label, href]) => {
            const isActive = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={isActive ? "page" : undefined}
                className={[
                  "rounded-lg border px-3 py-2 text-sm font-semibold transition",
                  isActive
                    ? "border-action bg-action text-white shadow-sm"
                    : "secondary-button",
                ].join(" ")}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </header>
      {children}
    </main>
  );
}
