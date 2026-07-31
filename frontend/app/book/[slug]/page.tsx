"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, api, formatNgn, Service, Slot, Staff, Tenant } from "../../../lib/api";
import {
  validateEmail,
  validatePhone,
  validateName,
  validateInspoImages,
  formatApiError,
  getFieldError,
  type ValidationResult,
} from "../../../lib/validations";

function PlantLeft() {
  return (
    <svg viewBox="0 0 200 300" fill="none" className="h-full w-full" aria-hidden="true">
      <path d="M10 300 C 30 220, 55 150, 95 80" stroke="#2d4236" strokeWidth="0.7" strokeLinecap="round" />
      <path d="M45 210 Q 15 190, 8 160 Q 22 140, 52 175 Z" fill="#b9ccbf" fillOpacity="0.3" stroke="#2d4236" strokeWidth="0.5" />
      <circle cx="8" cy="160" r="2" fill="#caa26b" />
      <path d="M60 170 Q 35 140, 42 110 Q 62 110, 70 142 Z" fill="#b9ccbf" fillOpacity="0.3" stroke="#2d4236" strokeWidth="0.5" />
      <path d="M78 130 Q 105 110, 115 80 Q 95 70, 85 105 Z" fill="#b9ccbf" fillOpacity="0.3" stroke="#2d4236" strokeWidth="0.5" />
    </svg>
  );
}

function PlantRight() {
  return (
    <svg viewBox="0 0 150 250" fill="none" className="h-full w-full" aria-hidden="true">
      <path d="M150 200 C 110 160, 90 110, 75 40" stroke="#2d4236" strokeWidth="0.7" />
      <path d="M115 155 Q 85 165, 78 185 Q 93 200, 113 170 Z" fill="#b9ccbf" fillOpacity="0.3" stroke="#2d4236" strokeWidth="0.5" />
      <circle cx="78" cy="185" r="2" fill="#caa26b" />
    </svg>
  );
}

function StepHeader({ number, title, subtitle, icon }: { number: string; title: string; subtitle: string; icon: "time" | "person" }) {
  return (
    <div className="flex items-center justify-between border-b border-line/60 pb-4">
      <div className="flex items-center gap-3.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-[#0e4731] to-[#1b5e43] text-xs font-bold text-white shadow-md shadow-action/10">
          {number}
        </span>
        <div>
          <h2 className="text-base font-bold tracking-normal text-ink">{title}</h2>
          <span className="mt-0.5 block text-[10px] font-bold uppercase tracking-wider text-ink/55">{subtitle}</span>
        </div>
      </div>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#f4f7f5] text-action">
        {icon === "time" ? (
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ) : (
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        )}
      </div>
    </div>
  );
}

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function bookingFieldName(field: string) {
  if (field === "client.full_name") return "full_name";
  if (field === "client.email") return "email";
  if (field === "client.phone") return "phone";
  if (field === "client.whatsapp_number") return "whatsapp_number";
  return field;
}

export default function PublicBookingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug ?? "";
  const bookingSectionRef = useRef<HTMLFormElement | null>(null);
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
  const [fieldErrors, setFieldErrors] = useState<Map<string, string>>(new Map());
  const selectedService = services.find((service) => service.id === serviceId);
  const selectedStaff = staff.find((member) => member.id === staffId);
  const minDate = formatDateInput(new Date());
  const maxDate = tenant ? formatDateInput(addDays(new Date(), tenant.advance_booking_days)) : undefined;
  const dateValidationError =
    date && date < minDate
      ? "Choose today or a future date."
      : date && maxDate && date > maxDate
        ? `Choose a date within the next ${tenant?.advance_booking_days ?? 0} days.`
        : "";
  const hasSlotInputs = Boolean(serviceId && date && !dateValidationError);
  const canSubmit = Boolean(serviceId && date && !dateValidationError && slot && fullName.trim() && email.trim()) && !submitLoading;
  const selectedDateLabel = date
    ? new Date(`${date}T00:00:00`).toLocaleDateString([], { month: "long", day: "numeric" })
    : "";
  const slotScopeLabel = selectedStaff ? selectedStaff.name : "any available staff";
  const slotHeading = hasSlotInputs ? `Times for ${slotScopeLabel} on ${selectedDateLabel}` : "Available times";

  useEffect(() => {
    if (!slug) return;
    api.tenant(slug).then(setTenant).catch((err) => setError(err.message));
    api.services(slug).then(setServices).catch((err) => setError(err.message));
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    setStaff([]);
    setStaffId("");
    setSlots([]);
    setSlot("");
    if (!serviceId) return;
    api.staff(slug, serviceId).then(setStaff).catch((err) => setError(err.message));
  }, [slug, serviceId]);

  useEffect(() => {
    if (!slug) return;
    setSlots([]);
    setSlot("");
    if (!serviceId || !date) return;
    if (dateValidationError) return;
    setSlotsLoading(true);
    setError("");
    api.slots(slug, serviceId, date, staffId || undefined)
      .then(setSlots)
      .catch((err) => setError(err.message))
      .finally(() => setSlotsLoading(false));
  }, [slug, serviceId, staffId, date, dateValidationError]);

  // Field-level validation on blur
  function validateField(fieldName: string, value: string) {
    const errors = new Map(fieldErrors);
    let result: ValidationResult;

    switch (fieldName) {
      case "full_name":
        result = validateName(value);
        break;
      case "email":
        result = validateEmail(value);
        break;
      case "phone":
        if (!value) {
          const nextErrors = new Map(fieldErrors);
          nextErrors.delete("phone");
          setFieldErrors(nextErrors);
          return;
        }
        result = validatePhone(value);
        break;
      case "whatsapp_number":
        if (!value) {
          const nextErrors = new Map(fieldErrors);
          nextErrors.delete("whatsapp_number");
          setFieldErrors(nextErrors);
          return;
        }
        result = validatePhone(value, "whatsapp_number");
        break;
      default:
        return;
    }

    if (result.valid) {
      errors.delete(fieldName);
    } else {
      const msg = getFieldError(result, fieldName);
      if (msg) errors.set(fieldName, msg);
    }
    setFieldErrors(errors);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!slug) {
      setError("Invalid booking link");
      return;
    }

    // Clear previous errors
    setError("");
    setFieldErrors(new Map());

    // Validate all fields
    const errors = new Map<string, string>();

    // Validate name
    const nameResult = validateName(fullName);
    if (!nameResult.valid) {
      nameResult.errors.forEach(e => errors.set(e.field, e.message));
    }

    // Validate email
    const emailResult = validateEmail(email);
    if (!emailResult.valid) {
      emailResult.errors.forEach(e => errors.set(e.field, e.message));
    }

    // Validate phone (if provided)
    if (phone) {
      const phoneResult = validatePhone(phone);
      if (!phoneResult.valid) {
        phoneResult.errors.forEach(e => errors.set(e.field, e.message));
      }
    }

    // Validate WhatsApp number (if provided)
    if (whatsappNumber) {
      const whatsappResult = validatePhone(whatsappNumber, "whatsapp_number");
      if (!whatsappResult.valid) {
        whatsappResult.errors.forEach(e => errors.set(e.field, e.message));
      }
    }

    // Validate images (if provided)
    if (inspoImages && inspoImages.length > 0) {
      const imagesResult = validateInspoImages(inspoImages);
      if (!imagesResult.valid) {
        imagesResult.errors.forEach(e => errors.set(e.field, e.message));
      }
    }

    if (errors.size > 0) {
      setFieldErrors(errors);
      setError("Please fix the errors below and try again.");
      return;
    }

    setSubmitLoading(true);
    try {
      // Normalize start_time with UTC timezone marker
      const startTimeWithTimezone = slot ? new Date(slot).toISOString() : "";
      if (!startTimeWithTimezone.endsWith("Z") && !startTimeWithTimezone.includes("+")) {
        // Ensure UTC timezone if not present
        const slotDate = new Date(slot);
        slotDate.setMilliseconds(0); // Clear milliseconds for consistency
      }

      // Clean phone numbers: remove spaces and dashes
      const cleanPhone = phone ? phone.replace(/[\s-]/g, "") : null;
      const cleanWhatsapp = whatsappNumber ? whatsappNumber.replace(/[\s-]/g, "") : null;

      const payload = {
        service_id: serviceId,
        staff_id: staffId || null,
        start_time: startTimeWithTimezone,
        client: {
          full_name: fullName,
          email,
          phone: cleanPhone,
          whatsapp_number: cleanWhatsapp,
        },
        notes: notes || null,
      };
      const body = new FormData();
      body.set("payload", JSON.stringify(payload));
      Array.from(inspoImages ?? []).forEach((file) => body.append("inspo_images", file));
      const response = await api.createBooking(slug, body);
      window.location.href = response.payment_url || response.manage_url;
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors.length > 0) {
        const apiErrors = new Map<string, string>();
        err.fieldErrors.forEach((fieldError) => apiErrors.set(bookingFieldName(fieldError.field), fieldError.message));
        setFieldErrors(apiErrors);
      }
      setError(formatApiError(err));
    } finally {
      setSubmitLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen justify-center overflow-hidden bg-[#f5f8f6] px-4 py-6 text-ink md:px-12 md:py-12">
      <div className="pointer-events-none absolute bottom-0 left-0 z-0 h-[500px] w-96 opacity-40">
        <PlantLeft />
      </div>
      <div className="pointer-events-none absolute right-0 top-0 z-0 h-96 w-80 opacity-40">
        <PlantRight />
      </div>

      <div className="relative z-10 grid w-full max-w-6xl grid-cols-1 items-start gap-8 lg:grid-cols-12">
        <aside className="space-y-4 lg:sticky lg:top-12 lg:col-span-4">
          <section className="relative overflow-hidden rounded-2xl border border-white/60 bg-white/70 p-8 shadow-[0_20px_50px_rgba(14,71,49,0.04)] backdrop-blur-xl">
            <div className="absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-gradient-to-bl from-[#caa26b]/10 to-transparent" />
            <span className="inline-flex items-center gap-1.5 rounded-md border border-action/10 bg-[#e1eae3] px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-action">
              <span className="h-1.5 w-1.5 rounded-full bg-action" />
              Book Online
            </span>
            <h1 className="mt-4 font-serif text-4xl font-normal tracking-normal text-ink">{tenant?.name ?? "Book Appointment"}</h1>
            <p className="mt-3 text-[13px] font-medium leading-relaxed text-ink/70">
              {tenant?.description || "Choose a service, pick a time, pay the deposit, and upload inspo if your look needs a quote."}
            </p>
            <div className="mt-8 space-y-3 border-t border-ink/5 pt-6">
              <p className="flex items-center gap-3 text-xs font-semibold text-[#3d5245]">
                <svg className="h-4 w-4 text-[#caa26b]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Secure payment
              </p>
              <p className="flex items-center gap-3 text-xs font-semibold text-[#3d5245]">
                <svg className="h-4 w-4 text-[#caa26b]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Booking confirmed after payment
              </p>
              {tenant?.address && <p className="text-xs font-semibold text-[#3d5245]">{tenant.address}</p>}
              {tenant?.phone && <p className="text-xs font-semibold text-[#3d5245]">{tenant.phone}</p>}
            </div>
          </section>
        </aside>

        <form ref={bookingSectionRef} onSubmit={submit} className="grid gap-10 rounded-2xl border border-white/80 bg-white/90 p-6 shadow-[0_30px_60px_rgba(14,71,49,0.05)] backdrop-blur-xl md:p-10 lg:col-span-8">
          <section className="grid gap-6">
            <StepHeader number="1" title="Service and time" subtitle="Step 1 of 2" icon="time" />

            <div className="grid items-start gap-5 md:grid-cols-2">
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Service
                <select className="rounded-xl bg-[#f8faf9]" value={serviceId} onChange={(event) => setServiceId(event.target.value)} required>
                  <option value="">Select service</option>
                  {services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}
                </select>
              </label>
              {tenant?.allow_staff_selection && (
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Staff
                  <select className="rounded-xl bg-[#f8faf9]" value={staffId} onChange={(event) => setStaffId(event.target.value)}>
                    <option value="">Any available staff</option>
                    {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                  </select>
                </label>
              )}
              <label className="grid gap-2 text-sm font-semibold text-ink/75 md:col-span-2">
                Date
                <input
                  className="rounded-xl bg-[#f8faf9]"
                  type="date"
                  value={date}
                  min={minDate}
                  max={maxDate}
                  onChange={(event) => setDate(event.target.value)}
                  required
                />
                <span className="text-xs font-normal text-ink/55">
                  Select a date from today{maxDate ? ` through ${new Date(`${maxDate}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}` : ""}.
                </span>
                {dateValidationError && <span className="text-xs font-semibold text-red-700">{dateValidationError}</span>}
              </label>
            </div>

            {selectedService && (
              <div className="grid gap-1 rounded-xl border border-line/70 bg-[#f8faf9] p-4 text-sm">
                <p className="font-semibold text-ink/75">{selectedService.price_label ?? formatNgn(selectedService.price)}</p>
                <p className="text-lg font-bold text-ink">Deposit due now: {formatNgn(selectedService.deposit_due_now ?? selectedService.price)}</p>
              </div>
            )}

            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-ink">{slotHeading}</p>
                  {hasSlotInputs && (
                    <p className="mt-1 text-xs font-medium text-ink/55">
                      {selectedStaff
                        ? `Only ${selectedStaff.name}'s open times are shown.`
                        : "These times have at least one eligible staff member available."}
                    </p>
                  )}
                </div>
                {slot && <p className="text-xs font-semibold text-action">Selected: {new Date(slot).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>}
              </div>
              {slotsLoading && <p className="muted">Loading times...</p>}
              {!slotsLoading && !serviceId && <p className="muted">Choose a service to see open times.</p>}
              {!slotsLoading && serviceId && !date && <p className="muted">Choose a date to see open times.</p>}
              {!slotsLoading && serviceId && date && dateValidationError && <p className="muted">{dateValidationError}</p>}
              {!slotsLoading && serviceId && date && !dateValidationError && slots.length === 0 && (
                <p className="muted">
                  {selectedStaff ? `No times for ${selectedStaff.name} on this date. Try another staff member or date.` : "No open times on this date. Try another date."}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {slots.map((item) => (
                  <button
                    key={item.start_time}
                    type="button"
                    aria-pressed={slot === item.start_time}
                    onClick={() => setSlot(item.start_time)}
                    className="slot-button rounded-xl"
                  >
                    {new Date(item.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="grid gap-6">
            <StepHeader number="2" title="Your details" subtitle="Step 2 of 2" icon="person" />
            <div className="grid gap-5 md:grid-cols-2">
              <div className="grid gap-1">
                <input
                  className="rounded-xl bg-[#f8faf9]"
                  name="full_name"
                  placeholder="Full name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  onBlur={() => validateField("full_name", fullName)}
                  required
                />
                {fieldErrors.get("full_name") && <p className="text-xs font-semibold text-red-700">{fieldErrors.get("full_name")}</p>}
              </div>

              <div className="grid gap-1">
                <input
                  className="rounded-xl bg-[#f8faf9]"
                  name="email"
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  onBlur={() => validateField("email", email)}
                  required
                />
                {fieldErrors.get("email") && <p className="text-xs font-semibold text-red-700">{fieldErrors.get("email")}</p>}
              </div>

              <div className="grid gap-1">
                <input
                  className="rounded-xl bg-[#f8faf9]"
                  name="phone"
                  placeholder="Phone (optional)"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  onBlur={() => validateField("phone", phone)}
                />
                {fieldErrors.get("phone") && <p className="text-xs font-semibold text-red-700">{fieldErrors.get("phone")}</p>}
              </div>

              <div className="grid gap-1">
                <input
                  className="rounded-xl bg-[#f8faf9]"
                  name="whatsapp_number"
                  placeholder="WhatsApp number (optional)"
                  value={whatsappNumber}
                  onChange={(event) => setWhatsappNumber(event.target.value)}
                  onBlur={() => validateField("whatsapp_number", whatsappNumber)}
                />
                {fieldErrors.get("whatsapp_number") && <p className="text-xs font-semibold text-red-700">{fieldErrors.get("whatsapp_number")}</p>}
              </div>

              <label className="group relative flex h-32 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-[#b9ccbf] bg-[#f8faf9] transition hover:border-action hover:bg-[#eff3f0] md:col-span-2">
                <div className="flex flex-col items-center justify-center">
                  <span className="mb-2.5 flex h-10 w-10 items-center justify-center rounded-xl border border-line/70 bg-white text-ink/60 shadow-sm transition group-hover:text-action">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 19.5h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5z" />
                    </svg>
                  </span>
                  <p className="text-xs font-bold text-ink">{inspoImages?.length ? `${inspoImages.length} image${inspoImages.length === 1 ? "" : "s"} selected` : "Upload inspo or reference images"}</p>
                  <p className="mt-1 text-[10px] font-medium text-ink/55">PNG or JPG images only</p>
                </div>
                <input
                  className="hidden"
                  name="inspo_images"
                  type="file"
                  accept="image/png,image/jpeg,image/jpg"
                  multiple
                  onChange={(event) => {
                    setInspoImages(event.target.files);
                    // Validate images on selection
                    if (event.target.files && event.target.files.length > 0) {
                      const result = validateInspoImages(event.target.files);
                      const errors = new Map(fieldErrors);
                      if (result.valid) {
                        errors.delete("inspo_images");
                      } else {
                        result.errors.forEach(e => errors.set(e.field, e.message));
                      }
                      setFieldErrors(errors);
                    }
                  }}
                />
              </label>
              {fieldErrors.get("inspo_images") && <p className="text-xs font-semibold text-red-700 md:col-span-2">{fieldErrors.get("inspo_images")}</p>}

              <textarea
                className="rounded-xl bg-[#f8faf9] md:col-span-2"
                name="notes"
                placeholder="Notes or style details..."
                rows={4}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </div>
          </section>

          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>}
          <button type="submit" disabled={!canSubmit} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#0e4731] to-[#17573d] text-sm font-semibold text-white shadow-lg shadow-action/10">
            <span>{submitLoading ? "Getting payment ready..." : "Continue to payment"}</span>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </button>
        </form>
      </div>

    </main>
  );
}
