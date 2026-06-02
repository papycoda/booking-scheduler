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

export function DashboardShell({ children }: { title: string; children: React.ReactNode }) {
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

  function logout() {
    clearAccessToken();
    window.location.href = "/login";
  }

  if (!isAuthorized) {
    return null;
  }

  return (
    <main className="page-shell">
      <header className="flex flex-wrap items-center justify-between gap-4 px-1 py-2">
        <Link href="/dashboard" className="flex items-center gap-3 rounded-xl text-ink transition hover:text-action">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#0e4731] text-lg font-black text-white shadow-sm">B</span>
          <span className="grid gap-0.5">
            <span className="text-xl font-bold leading-none tracking-normal">Bookie</span>
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-action">Business manager</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            href="/onboarding"
            className="hidden rounded-xl border border-line bg-white px-3 py-2 text-sm font-semibold text-ink/75 shadow-sm transition hover:text-action sm:inline-flex"
          >
            Setup guide
          </Link>
          <Link
            href="/dashboard/settings"
            className="grid h-10 w-10 place-items-center rounded-full border border-white bg-white text-sm font-bold text-action shadow-sm ring-4 ring-action/5"
            aria-label="Profile"
          >
            P
          </Link>
          <button
            type="button"
            onClick={logout}
            className="secondary-button inline-flex min-h-0 items-center gap-2 rounded-xl border-0 bg-transparent px-2 py-2 text-sm font-semibold text-ink/75 shadow-none hover:bg-transparent hover:text-action hover:shadow-none"
          >
            <span>Logout</span>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
            </svg>
          </button>
        </div>
      </header>

      <section className="dashboard-card overflow-hidden">
        <div className="p-3 sm:p-4">
          <nav className="flex gap-1 overflow-x-auto rounded-xl border border-line/60 bg-field/80 p-1">
            {links.map(([label, href]) => {
              const isActive = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  className={[
                    "whitespace-nowrap rounded-lg px-4 py-2 text-xs font-semibold transition",
                    isActive ? "bg-action text-white shadow-sm" : "text-ink/70 hover:bg-white hover:text-action",
                  ].join(" ")}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
      </section>

      {children}
    </main>
  );
}
