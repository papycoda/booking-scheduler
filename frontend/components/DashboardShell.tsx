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

  function logout() {
    clearAccessToken();
    window.location.href = "/login";
  }

  return (
    <main className="page-shell">
      <header className="grid gap-5 rounded-xl border border-line/80 bg-white/85 p-4 shadow-sm backdrop-blur sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Link href="/dashboard" className="flex items-center gap-3 rounded-lg text-ink transition hover:text-action">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-action text-lg font-black text-white shadow-sm">B</span>
            <span>
              <span className="block text-lg font-bold leading-none tracking-normal">Bookie</span>
              <span className="mt-1 block text-xs font-semibold uppercase tracking-[0.16em] text-action">Business dashboard</span>
            </span>
          </Link>

          <div className="flex items-center gap-2">
            <Link href="/dashboard/settings" className="secondary-button rounded-lg border px-3 py-2 text-sm font-semibold">
              Profile
            </Link>
            <button type="button" onClick={logout} className="secondary-button rounded-lg border px-3 py-2 text-sm font-semibold">
              Logout
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3 border-t border-line/70 pt-4">
          <div>
            <p className="eyebrow">Current section</p>
            <h1 className="mt-1 text-3xl font-semibold">{title}</h1>
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
        </div>
      </header>
      {children}
    </main>
  );
}
