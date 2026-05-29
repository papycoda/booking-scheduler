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
    <main className="mx-auto grid max-w-6xl gap-6 px-5 py-8">
      <nav className="flex flex-wrap gap-2 border-b border-line pb-4">
        {links.map(([label, href]) => (
          <Link key={href} href={href} className="border border-line bg-white px-3 py-2 text-sm font-semibold">
            {label}
          </Link>
        ))}
      </nav>
      <h1 className="text-3xl font-semibold">{title}</h1>
      {children}
    </main>
  );
}
