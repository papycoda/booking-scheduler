"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  apiAssetUrl,
  AnalyticsOverview,
  bookingStatusLabel,
  DashboardBooking,
  DashboardRescheduleRequest,
  formatNgn,
  paymentStatusLabel,
  payoutStatusLabel,
} from "../../lib/api";
import { DashboardShell } from "../../components/DashboardShell";

function isToday(value: string) {
  const date = new Date(value);
  const today = new Date();
  return date.toDateString() === today.toDateString();
}

function shortTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function shortDate(value: string) {
  return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function DashboardPage() {
  const [bookings, setBookings] = useState<DashboardBooking[]>([]);
  const [rescheduleRequests, setRescheduleRequests] = useState<DashboardRescheduleRequest[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [bookingRows, overview, requests] = await Promise.all([
        api.dashboardBookings(),
        api.dashboardAnalytics(),
        api.dashboardRescheduleRequests(),
      ]);
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

  const todaysBookings = useMemo(
    () => bookings.filter((booking) => isToday(booking.start_time) && !["cancelled", "expired"].includes(booking.status)),
    [bookings],
  );
  const payoutAttention = bookings.filter((booking) => booking.payment_id && ["queued", "pending", "failed", "needs_review", "needs_setup"].includes(booking.settlement_status ?? ""));
  const payoutReviewCount = bookings.filter((booking) => ["failed", "needs_review", "needs_setup"].includes(booking.settlement_status ?? "")).length;
  const depositsPaid = bookings.reduce((total, booking) => total + (booking.deposit_amount || 0), 0);
  const setupGaps = [
    bookings.length === 0 ? "Share your booking link" : "",
    payoutReviewCount > 0 ? "Check payouts" : "",
    rescheduleRequests.length > 0 ? "Review client time changes" : "",
  ].filter(Boolean);

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

  async function approvePayout(paymentId: string) {
    await api.approveDashboardPayout(paymentId);
    await load();
  }

  async function retryPayout(paymentId: string) {
    await api.retryDashboardPayout(paymentId);
    await load();
  }

  return (
    <DashboardShell title="Bookings">
      <section className="grid gap-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <article className="bookie-card p-4">
            <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#556e61]">Today</span>
            <strong className="mt-2 block text-2xl text-[#0f2119]">{todaysBookings.length}</strong>
            <p className="mt-1 text-xs font-medium text-[#556e61]">Bookings on the calendar</p>
          </article>
          <article className="bookie-card p-4">
            <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#556e61]">Deposits</span>
            <strong className="mt-2 block text-2xl text-[#0f2119]">{formatNgn(depositsPaid)}</strong>
            <p className="mt-1 text-xs font-medium text-[#556e61]">Paid through Bookie</p>
          </article>
          <article className="gold-card p-4">
            <span className="text-xs font-bold uppercase tracking-[0.12em]">Needs you</span>
            <strong className="mt-2 block text-2xl">{rescheduleRequests.length}</strong>
            <p className="mt-1 text-xs font-medium">Client{rescheduleRequests.length === 1 ? "" : "s"} asking to move</p>
          </article>
          <article className="bookie-card p-4">
            <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#556e61]">Payouts</span>
            <strong className="mt-2 block text-2xl text-[#0f2119]">{payoutAttention.length}</strong>
            <p className="mt-1 text-xs font-medium text-[#556e61]">Waiting or needs review</p>
          </article>
        </div>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="bookie-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-[#0f2119]">Today’s bookings</h1>
                <p className="bookie-subtitle mt-1">See who is coming in and what needs attention.</p>
              </div>
              <Link href="/dashboard/availability" className="secondary-button min-h-0 rounded-xl px-4 py-2 text-sm">
                View calendar
              </Link>
            </div>
            <div className="mt-5 grid gap-3">
              {todaysBookings.slice(0, 5).map((booking) => (
                <div key={booking.id} className="grid gap-3 rounded-2xl border border-slate-100 bg-[#f8faf9] p-4 sm:grid-cols-[auto_1fr_auto] sm:items-center">
                  <span className="grid h-12 w-16 place-items-center rounded-xl bg-[#e8efe9] text-sm font-bold text-[#0e4731]">{shortTime(booking.start_time)}</span>
                  <div>
                    <strong className="block text-[#0f2119]">{booking.client_name}</strong>
                    <span className="bookie-help">{booking.service_name} with {booking.staff_name}</span>
                  </div>
                  <span className="status-badge status-badge-success">{paymentStatusLabel(booking.payment_status)}</span>
                </div>
              ))}
              {todaysBookings.length === 0 && (
                <p className="soft-empty">No bookings for today. Share your booking link or check the calendar for the week ahead.</p>
              )}
            </div>
          </div>

          <aside className="grid gap-6">
            <section className="bookie-card p-5">
              <h2 className="section-title">Clients asking to move</h2>
              <div className="mt-4 grid gap-3">
                {rescheduleRequests.map((request) => (
                  <div key={request.id} className="rounded-2xl border border-[#caa26b]/35 bg-[#fffaf2] p-4">
                    <strong className="block text-[#0f2119]">{request.client_name}</strong>
                    <span className="mt-1 block text-sm font-medium text-[#7a5424]">
                      Wants {request.service_name} moved to {shortDate(request.requested_start_time)}
                    </span>
                    {request.client_note && <p className="mt-2 text-sm text-[#556e61]">{request.client_note}</p>}
                    <div className="mt-3 flex gap-2">
                      <button type="button" className="min-h-0 rounded-xl px-3 py-2 text-xs" onClick={() => decideReschedule(request.id, "approved")}>
                        Confirm move
                      </button>
                      <button type="button" className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" onClick={() => decideReschedule(request.id, "rejected")}>
                        Decline
                      </button>
                    </div>
                  </div>
                ))}
                {rescheduleRequests.length === 0 && <p className="soft-empty">No one has asked to move an appointment.</p>}
              </div>
            </section>

            <section className="bookie-card p-5">
              <h2 className="section-title">Setup gaps</h2>
              <div className="mt-4 grid gap-2">
                {setupGaps.map((gap) => (
                  <span key={gap} className="rounded-xl border border-slate-100 bg-[#f8faf9] px-3 py-2 text-sm font-semibold text-[#556e61]">{gap}</span>
                ))}
                {setupGaps.length === 0 && <p className="soft-empty">Everything important is ready for bookings.</p>}
              </div>
            </section>
          </aside>
        </section>

        <section className="bookie-card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5">
            <div>
              <h2 className="section-title">All bookings</h2>
              <p className="bookie-subtitle mt-1">
                {analytics?.bookings_count ?? bookings.length} total bookings. Top service: {analytics?.top_services[0]?.name ?? "none yet"}.
              </p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="bg-[#f8faf9]">
                <tr>
                  {["Client", "Booking", "Time", "Payment", "Payout", "Inspo", "Actions"].map((heading) => (
                    <th key={heading} className="p-4 text-xs font-bold uppercase tracking-wider text-[#556e61]">{heading}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bookings.map((booking) => (
                  <tr key={booking.id} className="border-t border-slate-100 align-top">
                    <td className="p-4">
                      <strong className="block text-[#0f2119]">{booking.client_name}</strong>
                      <span className="bookie-help">{booking.client_email}</span>
                    </td>
                    <td className="p-4">
                      <span className="block font-semibold text-[#0f2119]">{booking.service_name}</span>
                      <span className="bookie-help">with {booking.staff_name}</span>
                      {booking.cancelled_by && <span className="mt-1 block text-xs font-semibold text-red-700">Cancelled by {booking.cancelled_by}</span>}
                    </td>
                    <td className="p-4">{shortDate(booking.start_time)}</td>
                    <td className="p-4">
                      <span className="status-badge status-badge-success">{bookingStatusLabel(booking.status)}</span>
                      <span className="mt-2 block text-xs font-semibold text-[#556e61]">Deposit: {formatNgn(booking.deposit_amount)}</span>
                      {booking.quoted_price && <span className="block text-xs font-semibold text-[#556e61]">Quote: {formatNgn(booking.quoted_price)}</span>}
                    </td>
                    <td className="p-4">
                      <span className="block text-xs font-semibold text-[#556e61]">{payoutStatusLabel(booking.settlement_status)}</span>
                      <span className="block text-xs text-[#556e61]">Bookie fee: {formatNgn(booking.platform_fee_amount ?? 0)}</span>
                      <span className="block text-xs text-[#556e61]">Business: {formatNgn(booking.business_net_amount ?? 0)}</span>
                      {booking.payment_id && ["queued", "pending"].includes(booking.settlement_status ?? "") && (
                        <button className="secondary-button mt-2 min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => initiatePayout(booking.payment_id!)}>
                          Send payout
                        </button>
                      )}
                      {booking.payment_id && booking.settlement_status === "needs_review" && (
                        <button className="secondary-button mt-2 min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => approvePayout(booking.payment_id!)}>
                          Approve payout
                        </button>
                      )}
                      {booking.payment_id && booking.settlement_status === "failed" && (
                        <button className="secondary-button mt-2 min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => retryPayout(booking.payment_id!)}>
                          Retry payout
                        </button>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap -space-x-2">
                        {(booking.inspo_assets ?? []).map((asset) => {
                          const imageUrl = apiAssetUrl(asset.url);
                          return (
                            <a key={asset.id} href={imageUrl} target="_blank" rel="noreferrer" className="group relative inline-block">
                              <img src={imageUrl} alt={asset.original_filename} className="h-9 w-9 rounded-full border-2 border-white object-cover shadow-sm transition group-hover:z-10 group-hover:scale-105" />
                              <span className="pointer-events-none absolute left-1/2 top-11 z-20 hidden w-36 -translate-x-1/2 rounded-xl border border-white bg-white p-1 shadow-[0_18px_36px_rgba(14,71,49,0.18)] group-hover:block">
                                <img src={imageUrl} alt="" className="h-28 w-full rounded-lg object-cover" />
                                <span className="mt-1 block truncate px-1 text-[10px] font-semibold text-[#556e61]">{asset.original_filename}</span>
                              </span>
                            </a>
                          );
                        })}
                        {(booking.inspo_assets ?? []).length === 0 && <span className="bookie-help">None</span>}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap gap-2">
                        <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => updateStatus(booking.id, "completed")}>Mark done</button>
                        <button className="danger-link min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => updateStatus(booking.id, "cancelled")}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {bookings.length === 0 && <div className="p-5"><p className="soft-empty">No bookings yet. Once clients book, they will show up here.</p></div>}
        </section>
      </section>
      {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
    </DashboardShell>
  );
}
