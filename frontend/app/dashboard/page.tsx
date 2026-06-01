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
      {analytics && (
        <section className="grid gap-3 sm:grid-cols-3">
          <div className="metric"><strong>{analytics.bookings_count}</strong><span className="muted">Bookings</span></div>
          <div className="metric"><strong>{formatNgn(analytics.revenue)}</strong><span className="muted">Revenue</span></div>
          <div className="metric"><strong>{analytics.top_services[0]?.name ?? "None"}</strong><span className="muted">Top service</span></div>
        </section>
      )}
      <section className="panel grid gap-3">
        <div>
          <p className="eyebrow">Reschedule requests</p>
          <h2 className="section-title">Needs approval</h2>
        </div>
        {rescheduleRequests.length === 0 && <p className="muted">No pending reschedule requests.</p>}
        {rescheduleRequests.map((request) => (
          <div key={request.id} className="panel-muted grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
            <div className="grid gap-1">
              <strong>{request.client_name} - {request.service_name}</strong>
              <span className="text-sm text-ink/70">
                Current: {new Date(request.current_start_time).toLocaleString()} with {request.current_staff_name}
              </span>
              <span className="text-sm text-ink/70">
                Requested: {new Date(request.requested_start_time).toLocaleString()} with {request.requested_staff_name}
              </span>
              <span className="text-xs text-warning">Held until {new Date(request.hold_expires_at).toLocaleString()}</span>
              {request.client_note && <span className="text-sm text-ink/70">{request.client_note}</span>}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => decideReschedule(request.id, "approved")}>Approve</button>
              <button className="secondary-button" type="button" onClick={() => decideReschedule(request.id, "rejected")}>Reject</button>
            </div>
          </div>
        ))}
      </section>
      <section className="table-shell">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-field">
            <tr>
              <th className="p-3">Client</th>
              <th className="p-3">Service</th>
              <th className="p-3">Staff</th>
              <th className="p-3">Time</th>
              <th className="p-3">Status</th>
              <th className="p-3">Deposit / Quote</th>
              <th className="p-3">Settlement</th>
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
        </table>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
