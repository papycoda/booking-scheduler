"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatNgn, ManagedBooking, Slot } from "../../../../../lib/api";

export default function ManageBookingPage({
  params,
  searchParams,
}: {
  params: { slug: string; bookingId: string };
  searchParams: { token?: string };
}) {
  const token = searchParams.token ?? "";
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
    if (!token) {
      setError("Manage link is missing a token.");
      return;
    }
    try {
      setBooking(await api.managedBooking(params.slug, params.bookingId, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load booking");
    }
  }

  useEffect(() => {
    load();
  }, [params.slug, params.bookingId, token]);

  useEffect(() => {
    setSlots([]);
    setSelectedSlot("");
    if (!booking || !date || !token) return;
    setLoadingSlots(true);
    api.rescheduleSlots(params.slug, params.bookingId, token, date, booking.staff_id)
      .then(setSlots)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load slots"))
      .finally(() => setLoadingSlots(false));
  }, [booking?.staff_id, date, params.slug, params.bookingId, token]);

  async function cancelBooking() {
    if (!booking || !window.confirm("Cancel this booking? Deposits are non-refundable.")) return;
    setBusy(true);
    setError("");
    try {
      await api.cancelManagedBooking(params.slug, params.bookingId, token, cancelReason);
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
      await api.createRescheduleRequest(params.slug, params.bookingId, token, {
        start_time: selectedSlot,
        staff_id: booking?.staff_id,
        note: note || null,
      });
      setMessage("Reschedule request sent. The requested slot is held for 24 hours while the business reviews it.");
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
    <main className="page-shell">
      <section className="panel grid gap-4">
        <div>
          <p className="eyebrow">Manage booking</p>
          <h1 className="mt-1 text-3xl font-semibold">{booking?.service_name ?? "Booking details"}</h1>
        </div>
        {booking && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="panel-muted">
              <p className="muted">Status</p>
              <strong>{booking.booking_status}</strong>
            </div>
            <div className="panel-muted">
              <p className="muted">Time</p>
              <strong>{new Date(booking.start_time).toLocaleString()}</strong>
            </div>
            <div className="panel-muted">
              <p className="muted">Staff</p>
              <strong>{booking.staff_name}</strong>
            </div>
            <div className="panel-muted">
              <p className="muted">Deposit paid</p>
              <strong>{formatNgn(booking.deposit_amount)}</strong>
            </div>
          </div>
        )}
        <p className="rounded-lg border border-warning/25 bg-yellow-50 px-3 py-2 text-sm text-warning">
          Deposits are non-refundable. Cancelling or requesting a reschedule does not refund the deposit.
        </p>
        {message && <p className="rounded-lg border border-action/20 bg-green-50 px-3 py-2 text-sm text-action">{message}</p>}
        {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      </section>

      {booking && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="panel grid gap-3">
            <div>
              <p className="eyebrow">Cancel</p>
              <h2 className="section-title">Cancel this booking</h2>
              <p className="muted">Online cancellation is available until {new Date(booking.cancellation_deadline).toLocaleString()}.</p>
            </div>
            <textarea placeholder="Reason for cancellation" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} />
            <button className="danger-button" type="button" disabled={!booking.can_cancel || busy} onClick={cancelBooking}>
              Cancel booking
            </button>
          </div>

          <form onSubmit={requestReschedule} className="panel grid gap-3">
            <div>
              <p className="eyebrow">Reschedule</p>
              <h2 className="section-title">Request a new time</h2>
              <p className="muted">The business must approve the change. Requested slots are held for 24 hours.</p>
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
                  className="slot-button"
                  onClick={() => setSelectedSlot(item.start_time)}
                >
                  {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </button>
              ))}
            </div>
            {selectedSlot && <p className="tag w-fit">Requested: {new Date(selectedSlot).toLocaleString()}</p>}
            <textarea placeholder="Optional note for the business" value={note} onChange={(event) => setNote(event.target.value)} />
            <button type="submit" disabled={!selectedSlot || busy}>Request reschedule</button>
          </form>
        </section>
      )}

      {(booking?.pending_reschedule_requests ?? []).length > 0 && (
        <section className="panel grid gap-3">
          <div>
            <p className="eyebrow">Requests</p>
            <h2 className="section-title">Reschedule history</h2>
          </div>
          {(booking?.pending_reschedule_requests ?? []).map((request) => (
            <div key={request.id} className="panel-muted grid gap-1">
              <strong>{new Date(request.requested_start_time).toLocaleString()}</strong>
              <span className="muted">{request.status} with {request.staff_name ?? "staff"} until {new Date(request.hold_expires_at).toLocaleString()}</span>
              {request.client_note && <span className="text-sm text-ink/70">{request.client_note}</span>}
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
