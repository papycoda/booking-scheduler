"use client";

import { useEffect, useState } from "react";
import { api, apiAssetUrl, DashboardBooking, AnalyticsOverview, DashboardRescheduleRequest, formatNgn } from "../../lib/api";
import { DashboardShell } from "../../components/DashboardShell";

export default function DashboardPage() {
  const [bookings, setBookings] = useState<DashboardBooking[]>([]);
  const [rescheduleRequests, setRescheduleRequests] = useState<DashboardRescheduleRequest[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [bookingRows, overview, requests] = await Promise.all([api.dashboardBookings(), api.dashboardAnalytics(), api.dashboardRescheduleRequests()]);
      setBookings(bookingRows);
      setAnalytics(overview);
      setRescheduleRequests(requests);
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

  async function decideReschedule(requestId: string, decision: "approved" | "rejected") {
    await api.decideRescheduleRequest(requestId, { decision });
    await load();
  }

  async function initiatePayout(paymentId: string) {
    await api.initiateDashboardPayout(paymentId);
    await load();
  }

  return (
    <DashboardShell title="Bookings">
      <section className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="dashboard-card overflow-hidden lg:col-span-9">
          {analytics && (
            <div className="grid gap-3 border-b border-line/60 p-5 sm:grid-cols-3 sm:p-6">
              <div>
                <strong className="block text-2xl font-bold text-ink">{analytics.bookings_count}</strong>
                <span className="muted">Bookings</span>
              </div>
              <div>
                <strong className="block text-2xl font-bold text-ink">{formatNgn(analytics.revenue)}</strong>
                <span className="muted">Revenue</span>
              </div>
              <div>
                <strong className="block text-2xl font-bold text-ink">{analytics.top_services[0]?.name ?? "None"}</strong>
                <span className="muted">Top service</span>
              </div>
            </div>
          )}

          <div className="overflow-x-auto border-b border-line/60">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-[#fcfdfe]">
                <tr>
                  {["Client", "Service", "Staff", "Time", "Status", "Deposit / Quote", "Settlement", "Inspo", "Actions"].map((heading) => (
                    <th key={heading} className="p-3 text-[11px] font-bold uppercase tracking-wider text-ink/65">{heading}</th>
                  ))}
                </tr>
              </thead>
              {bookings.length > 0 && (
                <tbody>
                  {bookings.map((booking) => (
                    <tr key={booking.id} className="border-t border-line/70">
                      <td className="p-3">{booking.client_name}<span className="block text-xs text-ink/60">{booking.client_email}</span></td>
                      <td className="p-3">{booking.service_name}</td>
                      <td className="p-3">{booking.staff_name}</td>
                      <td className="p-3">{new Date(booking.start_time).toLocaleString()}</td>
                      <td className="p-3">{booking.status}</td>
                      <td className="p-3">
                        <span className="block">Deposit: {formatNgn(booking.deposit_amount)}</span>
                        <span className="block text-xs text-ink/60">{booking.price_status}{booking.quoted_price ? ` - Quote ${formatNgn(booking.quoted_price)}` : ""}</span>
                        {booking.client_notes && <span className="block text-xs text-ink/60">{booking.client_notes}</span>}
                        {booking.cancelled_by && <span className="block text-xs text-warning">Cancelled by {booking.cancelled_by}{booking.cancellation_reason ? `: ${booking.cancellation_reason}` : ""}</span>}
                      </td>
                      <td className="p-3">
                        <span className="block">{booking.collection_mode === "direct_split" ? "Direct split" : "Platform collected"}</span>
                        <span className="block text-xs text-ink/60">Fee: {formatNgn(booking.platform_fee_amount ?? 0)}</span>
                        <span className="block text-xs text-ink/60">Business: {formatNgn(booking.business_net_amount ?? 0)}</span>
                        <span className="block text-xs text-ink/60">Settlement: {booking.settlement_status ?? "not due"}</span>
                        {booking.payment_id && booking.settlement_status === "pending" && (
                          <button className="secondary-button mt-2" type="button" onClick={() => initiatePayout(booking.payment_id!)}>
                            Send payout
                          </button>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex flex-wrap gap-2">
                          {(booking.inspo_assets ?? []).map((asset) => (
                            <a key={asset.id} href={apiAssetUrl(asset.url)} target="_blank" rel="noreferrer" className="text-action underline">
                              {asset.original_filename}
                            </a>
                          ))}
                        </div>
                      </td>
                      <td className="flex gap-2 p-3">
                        <button className="secondary-button" type="button" onClick={() => updateStatus(booking.id, "completed")}>Done</button>
                        <button className="danger-button" type="button" onClick={() => updateStatus(booking.id, "cancelled")}>Cancel</button>
                        <button className="secondary-button" type="button" onClick={() => updateStatus(booking.id, "no_show")}>No Show</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              )}
            </table>
          </div>

          {bookings.length === 0 && (
            <div className="flex flex-col items-center justify-center px-6 py-20 text-center">
              <div className="relative mb-6 grid h-32 w-32 place-items-center rounded-full bg-[#eef3f0]">
                <svg className="h-24 w-24 text-[#2d473b]" viewBox="0 0 120 120" fill="none" aria-hidden="true">
                  <rect x="30" y="25" width="48" height="62" rx="5" stroke="currentColor" strokeWidth="1.8" fill="white" />
                  <path d="M46 18h16a3 3 0 013 3v5H43v-5a3 3 0 013-3z" fill="#cbdccf" stroke="currentColor" strokeWidth="1.8" />
                  <line x1="42" y1="42" x2="66" y2="42" stroke="#e2ece5" strokeWidth="2" strokeLinecap="round" />
                  <line x1="42" y1="54" x2="58" y2="54" stroke="#e2ece5" strokeWidth="2" strokeLinecap="round" />
                  <rect x="62" y="48" width="34" height="34" rx="5" stroke="currentColor" strokeWidth="1.8" fill="white" />
                  <path d="M62 57h34M71 48v34M87 48v34" stroke="#cbdccf" strokeWidth="1.2" />
                  <circle cx="68" cy="64" r="1.5" fill="currentColor" />
                  <circle cx="79" cy="64" r="1.5" fill="currentColor" />
                  <circle cx="79" cy="74" r="1.5" fill="currentColor" />
                  <path d="M36 82c3 8 10 10 10 10s4-15 11-19" stroke="#d08f52" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h2 className="text-xl font-bold tracking-normal text-ink">No bookings yet.</h2>
              <p className="mt-2 max-w-sm text-sm font-medium leading-relaxed text-ink/65">
                Share your public booking link or finish setting up services and availability so clients can book themselves.
              </p>
            </div>
          )}
        </div>

        <aside className="dashboard-card grid gap-4 p-5 lg:col-span-3">
          <div>
            <h2 className="text-base font-bold tracking-normal text-ink">Needs approval</h2>
            <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-ink/55">Reschedule requests</p>
          </div>
          {rescheduleRequests.length === 0 && <p className="border-t border-line/60 pt-4 text-xs font-medium text-ink/65">No pending reschedule requests.</p>}
          {rescheduleRequests.map((request) => (
            <div key={request.id} className="grid gap-3 border-t border-line/60 pt-4">
              <div className="grid gap-1">
                <strong className="text-sm">{request.client_name} - {request.service_name}</strong>
                <span className="text-xs text-ink/70">Current: {new Date(request.current_start_time).toLocaleString()}</span>
                <span className="text-xs text-ink/70">Requested: {new Date(request.requested_start_time).toLocaleString()}</span>
                <span className="text-xs text-warning">Held until {new Date(request.hold_expires_at).toLocaleString()}</span>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => decideReschedule(request.id, "approved")}>Approve</button>
                <button className="secondary-button" type="button" onClick={() => decideReschedule(request.id, "rejected")}>Reject</button>
              </div>
            </div>
          ))}
        </aside>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
