"use client";

import Link from "next/link";

const links = [
  ["Bookings", "/dashboard"],
  ["Services", "/dashboard/services"],
  ["Staff", "/dashboard/staff"],
  ["Availability", "/dashboard/availability"],
  ["Settings", "/dashboard/settings"],
];

export function DashboardShell({ title, children }: { title: string; children: React.ReactNode }) {
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
          {links.map(([label, href]) => (
            <Link key={href} href={href} className="secondary-button rounded-lg border px-3 py-2 text-sm font-semibold">
              {label}
            </Link>
          ))}
        </nav>
      </header>
      {children}
    </main>
  );
}
