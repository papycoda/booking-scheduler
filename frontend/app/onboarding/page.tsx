"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  api,
  AvailabilitySchedule,
  clearAccessToken,
  formatNgn,
  getAccessToken,
  koboToNgn,
  ngnToKobo,
  PaymentSetupStatus,
  Service,
  Staff,
  Tenant,
} from "../../lib/api";

const weekdays = [
  ["0", "Mon"],
  ["1", "Tue"],
  ["2", "Wed"],
  ["3", "Thu"],
  ["4", "Fri"],
  ["5", "Sat"],
  ["6", "Sun"],
];

export default function OnboardingPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [schedules, setSchedules] = useState<AvailabilitySchedule[]>([]);
  const [paymentStatus, setPaymentStatus] = useState<PaymentSetupStatus | null>(null);
  const [slugDraft, setSlugDraft] = useState("");
  const [publicOrigin, setPublicOrigin] = useState("");
  const [activeStep, setActiveStep] = useState("profile");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      clearAccessToken();
      window.location.replace("/login?next=/onboarding");
      return;
    }

    setPublicOrigin(window.location.origin);
    Promise.all([api.currentTenant(), api.dashboardServices(), api.dashboardStaff(), api.schedules(), api.paystackStatus()])
      .then(([tenantRow, serviceRows, staffRows, scheduleRows, payment]) => {
        setTenant(tenantRow);
        setSlugDraft(tenantRow.slug);
        setServices(serviceRows);
        setStaff(staffRows);
        setSchedules(scheduleRows);
        setPaymentStatus(payment);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load onboarding"))
      .finally(() => setIsLoading(false));
  }, []);

  function logout() {
    clearAccessToken();
    window.location.href = "/login";
  }

  function slugify(value: string) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 100);
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const updated = await api.updateTenant({
        slug: slugDraft,
        name: form.get("name"),
        description: form.get("description") || null,
        phone: form.get("phone") || null,
        address: form.get("address") || null,
        timezone: form.get("timezone"),
        default_deposit_amount: ngnToKobo(form.get("default_deposit_amount")),
        advance_booking_days: Number(form.get("advance_booking_days")),
        min_notice_hours: Number(form.get("min_notice_hours")),
        cancellation_notice_hours: Number(form.get("cancellation_notice_hours")),
        allow_staff_selection: true,
      });
      setTenant(updated);
      setSlugDraft(updated.slug);
      setActiveStep("service");
      setMessage("Business profile saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    }
  }

  async function createService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const service = await api.createService({
        name: form.get("name"),
        description: form.get("description") || null,
        duration_minutes: Number(form.get("duration_minutes")),
        price: ngnToKobo(form.get("price")),
        currency: "NGN",
        pricing_mode: form.get("pricing_mode"),
        deposit_policy: form.get("deposit_policy"),
        deposit_amount: form.get("deposit_policy") === "custom" ? ngnToKobo(form.get("deposit_amount")) : null,
        is_active: true,
      });
      setServices((current) => [service, ...current]);
      setActiveStep("staff");
      setMessage("Service added");
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create service");
    }
  }

  async function createStaff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const staffRow = await api.createStaff({
        name: form.get("name"),
        bio: form.get("bio") || null,
        is_bookable: true,
        is_active: true,
      });
      setStaff((current) => [staffRow, ...current]);
      setActiveStep("hours");
      setMessage("Staff member added");
      event.currentTarget.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create staff member");
    }
  }

  async function createWeeklyHours(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    const selectedDays = form.getAll("days").map(Number);
    const startTime = String(form.get("start_time"));
    const endTime = String(form.get("end_time"));
    const staffId = String(form.get("staff_id") || "");

    try {
      const created = await Promise.all(
        selectedDays.map((day) =>
          api.createSchedule({
            staff_id: staffId || null,
            day_of_week: day,
            start_time: startTime,
            end_time: endTime,
            is_active: true,
          }),
        ),
      );
      setSchedules((current) => [...created, ...current]);
      setActiveStep("payout");
      setMessage("Weekly hours added");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add weekly hours");
    }
  }

  async function savePayout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const status = await api.savePayoutSetup({
        account_name: form.get("account_name") || null,
        bank_code: form.get("bank_code"),
        account_number: form.get("account_number"),
      });
      setPaymentStatus(status);
      setActiveStep("launch");
      setMessage("Payout account saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save payout account");
    }
  }

  const publicBookingUrl = `${publicOrigin}/book/${slugDraft || tenant?.slug || ""}`;
  const completedSteps = [
    Boolean(tenant?.name && tenant?.slug),
    services.length > 0,
    staff.length > 0,
    schedules.length > 0,
    Boolean(paymentStatus?.payout_ready),
  ].filter(Boolean).length;

  if (isLoading) {
    return (
      <main className="page-shell">
        <section className="dashboard-card p-6">
          <p className="eyebrow">Bookie setup</p>
          <h1 className="section-title mt-2">Preparing your setup guide...</h1>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="flex flex-wrap items-center justify-between gap-4 px-1 py-2">
        <Link href="/dashboard" className="flex items-center gap-3 rounded-xl text-ink transition hover:text-action">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#0e4731] text-lg font-black text-white shadow-sm">B</span>
          <span className="grid gap-0.5">
            <span className="text-xl font-bold leading-none tracking-normal">Bookie</span>
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-action">Business setup</span>
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="rounded-xl border border-line bg-white px-3 py-2 text-sm font-semibold text-ink/75 shadow-sm transition hover:text-action"
          >
            Dashboard
          </Link>
          <button
            type="button"
            onClick={logout}
            className="secondary-button inline-flex min-h-0 items-center rounded-xl border-0 bg-transparent px-2 py-2 text-sm font-semibold text-ink/75 shadow-none hover:bg-transparent hover:text-action hover:shadow-none"
          >
            Logout
          </button>
        </div>
      </header>

      <section className="dashboard-card grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="eyebrow">Setup guide</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">Launch a clean booking flow</h1>
          <p className="muted mt-2 max-w-2xl">
            Set the business link, add one bookable service, assign staff, open weekly hours, and add payout details when ready.
          </p>
        </div>
        <div className="rounded-2xl border border-action/15 bg-action/5 p-4">
          <p className="text-sm font-semibold text-action">{completedSteps} of 5 complete</p>
          <div className="mt-3 h-2 w-48 overflow-hidden rounded-full bg-white">
            <div className="h-full rounded-full bg-action" style={{ width: `${(completedSteps / 5) * 100}%` }} />
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="dashboard-card h-fit p-4 lg:sticky lg:top-6">
          <p className="eyebrow">Steps</p>
          <nav className="mt-4 grid gap-1">
            {[
              ["profile", "Business profile"],
              ["service", "First service"],
              ["staff", "Staff"],
              ["hours", "Weekly hours"],
              ["payout", "Payouts"],
              ["launch", "Launch"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveStep(id)}
                className={`min-h-0 justify-start rounded-xl border-0 px-3 py-2 text-left text-sm shadow-none ${
                  activeStep === id ? "bg-field text-action" : "bg-transparent text-ink/65 hover:bg-field hover:text-action hover:shadow-none"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <div className="grid gap-6">
          {message && <p className="rounded-xl border border-action/15 bg-action/5 px-4 py-3 text-sm font-semibold text-action">{message}</p>}
          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}

          {activeStep === "profile" && (
            <form onSubmit={saveProfile} className="dashboard-card grid gap-5 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <p className="eyebrow">Step 1</p>
                <h2 className="section-title">Business profile and booking link</h2>
              </div>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Business name
                <input name="name" defaultValue={tenant?.name ?? ""} required />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Timezone
                <input name="timezone" defaultValue={tenant?.timezone ?? "Africa/Lagos"} required />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75 sm:col-span-2">
                Booking URL
                <div className="grid gap-3 sm:grid-cols-[auto_1fr_auto]">
                  <input readOnly value={`${publicOrigin}/book/`} className="bg-white text-ink/55" />
                  <input value={slugDraft} onChange={(event) => setSlugDraft(slugify(event.target.value))} required />
                  <button type="button" className="secondary-button" onClick={() => setSlugDraft(slugify(tenant?.name || "bookie-business"))}>
                    Generate
                  </button>
                </div>
                <span className="text-xs font-normal text-ink/55">{publicBookingUrl}</span>
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Default deposit (NGN)
                <input name="default_deposit_amount" type="number" min={0} step={1} defaultValue={koboToNgn(tenant?.default_deposit_amount)} />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Advance booking window
                <input name="advance_booking_days" type="number" min={1} defaultValue={tenant?.advance_booking_days ?? 30} />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Minimum notice
                <input name="min_notice_hours" type="number" min={0} defaultValue={tenant?.min_notice_hours ?? 2} />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Cancellation notice
                <input name="cancellation_notice_hours" type="number" min={0} defaultValue={tenant?.cancellation_notice_hours ?? 24} />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Phone
                <input name="phone" defaultValue={tenant?.phone ?? ""} placeholder="+234..." />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Address
                <input name="address" defaultValue={tenant?.address ?? ""} placeholder="Business address" />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75 sm:col-span-2">
                Public description
                <textarea name="description" defaultValue={tenant?.description ?? ""} placeholder="What clients should know before booking." />
              </label>
              <button type="submit" className="sm:col-span-2">Save and continue</button>
            </form>
          )}

          {activeStep === "service" && (
            <section className="grid gap-4">
              <form onSubmit={createService} className="dashboard-card grid gap-5 p-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <p className="eyebrow">Step 2</p>
                  <h2 className="section-title">Add the first service clients can book</h2>
                </div>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Service name
                  <input name="name" placeholder="Braids consultation" required />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Duration
                  <input name="duration_minutes" type="number" min={5} step={5} defaultValue={60} required />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Price or starting price (NGN)
                  <input name="price" type="number" min={0} step={1} defaultValue={25000} required />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Pricing style
                  <select name="pricing_mode" defaultValue="fixed">
                    <option value="fixed">Fixed</option>
                    <option value="from">From / starts at</option>
                    <option value="consultation">Consultation-based</option>
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Deposit rule
                  <select name="deposit_policy" defaultValue="tenant_default">
                    <option value="tenant_default">Use business default</option>
                    <option value="custom">Custom for this service</option>
                    <option value="disabled">No deposit</option>
                  </select>
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Custom deposit (NGN)
                  <input name="deposit_amount" type="number" min={0} step={1} placeholder="Only needed for custom" />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75 sm:col-span-2">
                  Description
                  <textarea name="description" placeholder="What is included, what clients should bring, or how pricing works." />
                </label>
                <button type="submit" className="sm:col-span-2">Add service</button>
              </form>
              {services.length > 0 && (
                <div className="dashboard-card grid gap-3 p-5">
                  <p className="eyebrow">Current services</p>
                  {services.map((service) => (
                    <div key={service.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line/70 bg-field/50 p-3">
                      <span className="font-semibold text-ink">{service.name}</span>
                      <span className="muted">{service.price_label ?? formatNgn(service.price)}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeStep === "staff" && (
            <section className="grid gap-4">
              <form onSubmit={createStaff} className="dashboard-card grid gap-5 p-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <p className="eyebrow">Step 3</p>
                  <h2 className="section-title">Add who clients can book with</h2>
                </div>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Staff name
                  <input name="name" placeholder="Yemi Ade" required />
                </label>
                <label className="grid gap-2 text-sm font-semibold text-ink/75">
                  Short bio
                  <input name="bio" placeholder="Stylist, colorist, consultant..." />
                </label>
                <button type="submit" className="sm:col-span-2">Add staff</button>
              </form>
              {staff.length > 0 && (
                <div className="dashboard-card grid gap-3 p-5">
                  <p className="eyebrow">Bookable staff</p>
                  {staff.map((staffRow) => (
                    <div key={staffRow.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line/70 bg-field/50 p-3">
                      <span className="font-semibold text-ink">{staffRow.name}</span>
                      <span className="status-badge status-badge-success">Bookable</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {activeStep === "hours" && (
            <section className="grid gap-4">
              <form onSubmit={createWeeklyHours} className="dashboard-card grid gap-5 p-5">
                <div>
                  <p className="eyebrow">Step 4</p>
                  <h2 className="section-title">Open weekly booking hours</h2>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <label className="grid gap-2 text-sm font-semibold text-ink/75">
                    Staff
                    <select name="staff_id" defaultValue={staff[0]?.id ?? ""}>
                      <option value="">All staff</option>
                      {staff.map((staffRow) => (
                        <option key={staffRow.id} value={staffRow.id}>
                          {staffRow.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-2 text-sm font-semibold text-ink/75">
                    Start
                    <input name="start_time" type="time" defaultValue="09:00" required />
                  </label>
                  <label className="grid gap-2 text-sm font-semibold text-ink/75">
                    End
                    <input name="end_time" type="time" defaultValue="17:00" required />
                  </label>
                </div>
                <fieldset className="grid gap-3">
                  <legend className="text-sm font-semibold text-ink/75">Days</legend>
                  <div className="flex flex-wrap gap-2">
                    {weekdays.map(([value, label]) => (
                      <label key={value} className="tag-button has-[:checked]:border-action has-[:checked]:bg-action has-[:checked]:text-white">
                        <input className="sr-only" type="checkbox" name="days" value={value} defaultChecked={["0", "1", "2", "3", "4"].includes(value)} />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <button type="submit">Add weekly hours</button>
              </form>
              {schedules.length > 0 && (
                <div className="dashboard-card grid gap-3 p-5">
                  <p className="eyebrow">Current weekly hours</p>
                  <p className="muted">{schedules.length} schedule block{schedules.length === 1 ? "" : "s"} saved.</p>
                </div>
              )}
            </section>
          )}

          {activeStep === "payout" && (
            <form onSubmit={savePayout} className="dashboard-card grid gap-5 p-5 sm:grid-cols-3">
              <div className="sm:col-span-3">
                <p className="eyebrow">Step 5</p>
                <h2 className="section-title">Add payout details</h2>
                <p className="muted mt-1">Clients can pay deposits before this is complete. Add bank details when you are ready to receive settlements.</p>
              </div>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Account name
                <input name="account_name" defaultValue={tenant?.payout_account_name ?? tenant?.name ?? ""} />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Bank code
                <input name="bank_code" defaultValue={tenant?.payout_bank_code ?? ""} placeholder="Example: 058" required />
              </label>
              <label className="grid gap-2 text-sm font-semibold text-ink/75">
                Account number
                <input name="account_number" defaultValue={tenant?.payout_account_number ?? ""} placeholder="10-digit account number" required />
              </label>
              <div className="flex flex-wrap gap-3 sm:col-span-3">
                <button type="submit">Save payout details</button>
                <button type="button" className="secondary-button" onClick={() => setActiveStep("launch")}>
                  Skip for now
                </button>
              </div>
            </form>
          )}

          {activeStep === "launch" && (
            <section className="dashboard-card grid gap-5 p-5">
              <div>
                <p className="eyebrow">Launch</p>
                <h2 className="section-title">Your booking flow is ready to test</h2>
                <p className="muted mt-1">Open the public link, choose a service and slot, then confirm the client-facing flow feels right.</p>
              </div>
              <div className="grid gap-3 rounded-2xl border border-line/70 bg-field/60 p-4">
                <span className="text-sm font-semibold text-ink">Public booking link</span>
                <a className="break-all text-sm font-semibold text-action underline-offset-4 hover:underline" href={publicBookingUrl} target="_blank" rel="noreferrer">
                  {publicBookingUrl}
                </a>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link href="/dashboard" className="button">Go to dashboard</Link>
                <Link href="/dashboard/settings" className="secondary-button">Fine-tune settings</Link>
              </div>
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
