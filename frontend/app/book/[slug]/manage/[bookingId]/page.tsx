"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api, bookingStatusLabel, formatNgn, ManagedBooking, Slot } from "../../../../../lib/api";

export default function ManageBookingPage() {
  return (
    <Suspense fallback={null}>
      <ManageBooking />
    </Suspense>
  );
}

function ManageBooking() {
  const params = useParams<{ slug: string; bookingId: string }>();
  const searchParams = useSearchParams();
  const slug = params.slug ?? "";
  const bookingId = params.bookingId ?? "";
  const token = searchParams.get("token") ?? "";
  const [booking, setBooking] = useState<ManagedBooking | null>(null);
  const [date, setDate] = useState("");
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [note, setNote] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!slug || !bookingId) {
      setError("Manage link is incomplete.");
      return;
    }
    if (!token) {
      setError("Manage link is missing a token.");
      return;
    }
    try {
      setBooking(await api.managedBooking(slug, bookingId, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load booking");
    }
  }

  useEffect(() => {
    load();
  }, [slug, bookingId, token]);

  useEffect(() => {
    if (!booking || booking.payment_status !== "pending" || booking.payment_url || !token) return;
    const timer = window.setInterval(() => {
      api.managedBooking(slug, bookingId, token).then(setBooking).catch(() => undefined);
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [booking?.payment_status, booking?.payment_url, slug, bookingId, token]);

  useEffect(() => {
    setSlots([]);
    setSelectedSlot("");
    if (!booking || !date || !token) return;
    setLoadingSlots(true);
    api.rescheduleSlots(slug, bookingId, token, date, booking.staff_id)
      .then(setSlots)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load slots"))
      .finally(() => setLoadingSlots(false));
  }, [booking?.staff_id, date, slug, bookingId, token]);

  async function cancelBooking() {
    if (!booking || !window.confirm("Cancel this booking? Deposits are non-refundable.")) return;
    setBusy(true);
    setError("");
    try {
      await api.cancelManagedBooking(slug, bookingId, token, cancelReason);
      setMessage("Booking cancelled. Deposit remains non-refundable.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel booking");
    } finally {
      setBusy(false);
    }
  }

  async function requestReschedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSlot) return;
    setBusy(true);
    setError("");
    try {
      await api.createRescheduleRequest(slug, bookingId, token, {
        start_time: selectedSlot,
        staff_id: booking?.staff_id,
        note: note || null,
      });
      setMessage("Request sent. This time is held while the business checks it.");
      setDate("");
      setSlots([]);
      setSelectedSlot("");
      setNote("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request reschedule");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f8f6] px-4 py-8 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto grid w-full max-w-5xl gap-6">
        <section className="public-glass grid gap-5 p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Your booking</p>
              <h1 className="mt-2 text-3xl font-bold tracking-normal">{booking?.service_name ?? "Booking details"}</h1>
            </div>
            {booking && <span className="status-badge status-badge-success">{bookingStatusLabel(booking.booking_status)}</span>}
          </div>

          {booking && (
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="finance-card">
                <p className="muted">Appointment time</p>
                <strong className="mt-1 block text-sm">{new Date(booking.start_time).toLocaleString()}</strong>
              </div>
              <div className="finance-card">
                <p className="muted">Staff</p>
                <strong className="mt-1 block text-sm">{booking.staff_name}</strong>
              </div>
              <div className="finance-card">
                <p className="muted">{booking.payment_status === "success" ? "Deposit paid" : "Deposit due"}</p>
                <strong className="mt-1 block text-sm">{formatNgn(booking.deposit_amount)}</strong>
              </div>
              <div className="finance-card">
                <p className="muted">Final price</p>
                <strong className="mt-1 block text-sm">{booking.quoted_price ? formatNgn(booking.quoted_price) : "To be agreed"}</strong>
              </div>
            </div>
          )}

          {booking?.payment_status === "success" ? (
            <p className="rounded-xl border border-action/20 bg-green-50 px-4 py-3 text-sm font-medium text-action">
              Payment received. Your booking is confirmed.
            </p>
          ) : booking?.payment_url ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#caa26b]/35 bg-[#fffaf2] px-4 py-3">
              <p className="text-sm font-medium text-[#7a5424]">Your booking is reserved while payment is pending.</p>
              <a className="button rounded-xl px-4 py-2 text-sm" href={booking.payment_url}>
                Pay deposit
              </a>
            </div>
          ) : booking?.payment_status === "pending" ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#caa26b]/35 bg-[#fffaf2] px-4 py-3">
              <p className="text-sm font-medium text-[#7a5424]">
                Your booking is saved. We are preparing the payment link and will refresh this page automatically.
              </p>
              <button className="secondary-button rounded-xl px-4 py-2 text-sm" type="button" onClick={() => void load()}>
                Check again
              </button>
            </div>
          ) : null}
          {booking?.payment_status === "success" && (
            <p className="rounded-xl border border-[#caa26b]/35 bg-[#fffaf2] px-4 py-3 text-sm font-medium text-[#7a5424]">
              Deposit is not refunded when you cancel or ask to move the booking.
            </p>
          )}
          {message && <p className="rounded-xl border border-action/20 bg-green-50 px-4 py-3 text-sm font-medium text-action">{message}</p>}
          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>}
        </section>

        {booking && (
          <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <form onSubmit={requestReschedule} className="public-glass grid gap-4 p-6">
              <div>
                <p className="eyebrow">Move booking</p>
                <h2 className="section-title">Ask for a new time</h2>
                <p className="muted mt-1">Pick a new time. The business will confirm if it works.</p>
              </div>
              <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
              {loadingSlots && <p className="muted">Loading times...</p>}
              {!loadingSlots && date && slots.length === 0 && <p className="muted">No times available for this date.</p>}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {slots.map((item) => (
                  <button
                    key={item.start_time}
                    type="button"
                    aria-pressed={selectedSlot === item.start_time}
                    className="slot-button rounded-xl"
                    onClick={() => setSelectedSlot(item.start_time)}
                  >
                    {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </button>
                ))}
              </div>
              {selectedSlot && <p className="tag w-fit">New time: {new Date(selectedSlot).toLocaleString()}</p>}
              <textarea placeholder="Optional note for the business" value={note} onChange={(event) => setNote(event.target.value)} />
              <button type="submit" disabled={!selectedSlot || busy}>Ask to move booking</button>
            </form>

            <section className="public-glass grid gap-4 p-6">
              <div>
                <p className="eyebrow">Cancel</p>
                <h2 className="section-title">Cancel this booking</h2>
                <p className="muted mt-1">You can cancel until {new Date(booking.cancellation_deadline).toLocaleString()}.</p>
              </div>
              <textarea placeholder="Reason for cancelling" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} />
              <button className="danger-link" type="button" disabled={!booking.can_cancel || busy} onClick={cancelBooking}>
                Cancel booking
              </button>
            </section>
          </section>
        )}

        {(booking?.pending_reschedule_requests ?? []).length > 0 && (
          <section className="public-glass grid gap-3 p-6">
            <div>
              <p className="eyebrow">Requests</p>
              <h2 className="section-title">Move requests</h2>
            </div>
            {(booking?.pending_reschedule_requests ?? []).map((request) => (
              <div key={request.id} className="rounded-2xl border border-line/70 bg-[#fcfdfe] p-4">
                <strong>{new Date(request.requested_start_time).toLocaleString()}</strong>
                <span className="muted mt-1 block">Reviewing with {request.staff_name ?? "staff"} until {new Date(request.hold_expires_at).toLocaleString()}</span>
                {request.client_note && <span className="mt-1 block text-sm text-ink/70">{request.client_note}</span>}
              </div>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
