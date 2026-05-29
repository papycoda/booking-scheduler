"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Service, Slot, Staff, Tenant } from "../../../lib/api";

export default function PublicBookingPage({ params }: { params: { slug: string } }) {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [staffId, setStaffId] = useState("");
  const [date, setDate] = useState("");
  const [slot, setSlot] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [inspoImages, setInspoImages] = useState<FileList | null>(null);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [error, setError] = useState("");
  const selectedService = services.find((service) => service.id === serviceId);
  const canSubmit = Boolean(serviceId && date && slot && fullName.trim() && email.trim()) && !submitLoading;

  useEffect(() => {
    api.tenant(params.slug).then(setTenant).catch((err) => setError(err.message));
    api.services(params.slug).then(setServices).catch((err) => setError(err.message));
  }, [params.slug]);

  useEffect(() => {
    setStaff([]);
    setStaffId("");
    setSlots([]);
    setSlot("");
    if (!serviceId) return;
    api.staff(params.slug, serviceId).then(setStaff).catch((err) => setError(err.message));
  }, [params.slug, serviceId]);

  useEffect(() => {
    setSlots([]);
    setSlot("");
    if (!serviceId || !date) return;
    setSlotsLoading(true);
    setError("");
    api.slots(params.slug, serviceId, date, staffId || undefined)
      .then(setSlots)
      .catch((err) => setError(err.message))
      .finally(() => setSlotsLoading(false));
  }, [params.slug, serviceId, staffId, date]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitLoading(true);
    try {
      const payload = {
        service_id: serviceId,
        staff_id: staffId || null,
        start_time: slot,
        client: {
          full_name: fullName,
          email,
          phone: phone || null,
          whatsapp_number: whatsappNumber || null,
        },
        notes: notes || null,
      };
      const body = new FormData();
      body.set("payload", JSON.stringify(payload));
      Array.from(inspoImages ?? []).forEach((file) => body.append("inspo_images", file));
      const response = await api.createBooking(params.slug, body);
      window.location.href = response.payment_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create booking");
    } finally {
      setSubmitLoading(false);
    }
  }

  return (
    <main className="mx-auto grid max-w-3xl gap-6 px-5 py-8">
      <header>
        <h1 className="text-3xl font-semibold">{tenant?.name ?? "Book Appointment"}</h1>
        {tenant?.description && <p className="mt-2 text-ink/70">{tenant.description}</p>}
      </header>
      <form onSubmit={submit} className="grid gap-5">
        <select value={serviceId} onChange={(event) => setServiceId(event.target.value)} required>
          <option value="">Select service</option>
          {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
        </select>
        {tenant?.allow_staff_selection && (
          <select value={staffId} onChange={(event) => setStaffId(event.target.value)}>
            <option value="">Anyone available</option>
            {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
          </select>
        )}
        <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
        {selectedService && (
          <div className="border border-line bg-white p-4 text-sm">
            <p>{selectedService.price_label ?? `${selectedService.currency} ${selectedService.price}`}</p>
            <p className="font-semibold">Deposit due now: {selectedService.currency} {selectedService.deposit_due_now ?? selectedService.price}</p>
          </div>
        )}
        {slotsLoading && <p className="text-sm text-ink/70">Loading times...</p>}
        {!slotsLoading && serviceId && date && slots.length === 0 && <p className="text-sm text-ink/70">No times available for this date.</p>}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {slots.map((item) => (
            <button
              key={item.start_time}
              type="button"
              aria-pressed={slot === item.start_time}
              onClick={() => setSlot(item.start_time)}
              className={slot === item.start_time ? "border-action bg-action text-white" : ""}
            >
              {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </button>
          ))}
        </div>
        {slot && <p className="text-sm text-action">Selected time: {new Date(slot).toLocaleString()}</p>}
        <input name="full_name" placeholder="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
        <input name="email" type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <input name="phone" placeholder="Phone" value={phone} onChange={(event) => setPhone(event.target.value)} />
        <input name="whatsapp_number" placeholder="WhatsApp number" value={whatsappNumber} onChange={(event) => setWhatsappNumber(event.target.value)} />
        <input name="inspo_images" type="file" accept="image/*" multiple onChange={(event) => setInspoImages(event.target.files)} />
        <textarea name="notes" placeholder="Notes" rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit" disabled={!canSubmit}>{submitLoading ? "Preparing payment..." : "Continue to Payment"}</button>
      </form>
    </main>
  );
}
