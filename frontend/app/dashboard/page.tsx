"use client";

import { useEffect, useState } from "react";
import { api, DashboardBooking, AnalyticsOverview } from "../../lib/api";
import { DashboardShell } from "../../components/DashboardShell";

export default function DashboardPage() {
  const [bookings, setBookings] = useState<DashboardBooking[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [bookingRows, overview] = await Promise.all([api.dashboardBookings(), api.dashboardAnalytics()]);
      setBookings(bookingRows);
      setAnalytics(overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load bookings");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function updateStatus(bookingId: string, status: string) {
    await api.updateDashboardBooking(bookingId, { status });
    await load();
  }

  return (
    <DashboardShell title="Bookings">
      {analytics && (
        <section className="grid gap-3 sm:grid-cols-3">
          <div className="border border-line bg-white p-4"><strong>{analytics.bookings_count}</strong><span className="block text-sm">Bookings</span></div>
          <div className="border border-line bg-white p-4"><strong>NGN {analytics.revenue}</strong><span className="block text-sm">Revenue</span></div>
          <div className="border border-line bg-white p-4"><strong>{analytics.top_services[0]?.name ?? "None"}</strong><span className="block text-sm">Top service</span></div>
        </section>
      )}
      <section className="overflow-x-auto border border-line bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-field">
            <tr>
              <th className="p-3">Client</th>
              <th className="p-3">Service</th>
              <th className="p-3">Staff</th>
              <th className="p-3">Time</th>
              <th className="p-3">Status</th>
              <th className="p-3">Deposit / Quote</th>
              <th className="p-3">Inspo</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {bookings.map((booking) => (
              <tr key={booking.id} className="border-t border-line">
                <td className="p-3">{booking.client_name}<span className="block text-xs text-ink/60">{booking.client_email}</span></td>
                <td className="p-3">{booking.service_name}</td>
                <td className="p-3">{booking.staff_name}</td>
                <td className="p-3">{new Date(booking.start_time).toLocaleString()}</td>
                <td className="p-3">{booking.status}</td>
                <td className="p-3">
                  <span className="block">Deposit: NGN {booking.deposit_amount}</span>
                  <span className="block text-xs text-ink/60">{booking.price_status}{booking.quoted_price ? ` - Quote NGN ${booking.quoted_price}` : ""}</span>
                  {booking.client_notes && <span className="block text-xs text-ink/60">{booking.client_notes}</span>}
                </td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-2">
                    {(booking.inspo_assets ?? []).map((asset) => (
                      <a key={asset.id} href={asset.url} target="_blank" rel="noreferrer" className="text-action underline">
                        {asset.original_filename}
                      </a>
                    ))}
                  </div>
                </td>
                <td className="flex gap-2 p-3">
                  <button type="button" onClick={() => updateStatus(booking.id, "completed")}>Done</button>
                  <button type="button" onClick={() => updateStatus(booking.id, "cancelled")}>Cancel</button>
                  <button type="button" onClick={() => updateStatus(booking.id, "no_show")}>No Show</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
