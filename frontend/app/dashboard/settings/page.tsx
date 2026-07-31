"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, koboToNgn, ngnToKobo, PaymentSetupStatus, Tenant } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const sectionLinks = [
  ["Booking link", "booking-link"],
  ["Business details", "business-details"],
  ["Booking rules", "booking-rules"],
  ["WhatsApp front desk", "whatsapp-front-desk"],
  ["Deposits", "deposits"],
  ["Payments", "payments"],
  ["Payout account", "payout-account"],
];

export default function SettingsPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<PaymentSetupStatus | null>(null);
  const [slugDraft, setSlugDraft] = useState("");
  const [publicOrigin, setPublicOrigin] = useState("");
  const [activeSection, setActiveSection] = useState("booking-link");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [payoutWarning, setPayoutWarning] = useState("");

  useEffect(() => {
    setPublicOrigin(window.location.origin);
    Promise.all([api.currentTenant(), api.paystackStatus()])
      .then(([tenantRow, status]) => {
        setTenant(tenantRow);
        setSlugDraft(tenantRow.slug);
        setPaymentStatus(status);
        if (status.warning_message) {
          setPayoutWarning(status.warning_message);
        }
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    function updateActiveSection() {
      const anchorLine = 140;
      const sections = sectionLinks
        .map(([, id]) => document.getElementById(id))
        .filter((section): section is HTMLElement => Boolean(section));

      const current =
        sections
          .map((section) => ({ id: section.id, top: section.getBoundingClientRect().top }))
          .filter((section) => section.top <= anchorLine)
          .sort((a, b) => b.top - a.top)[0] ?? sections[0];

      if (current?.id) setActiveSection(current.id);
    }

    updateActiveSection();
    window.addEventListener("scroll", updateActiveSection, { passive: true });
    window.addEventListener("resize", updateActiveSection);
    return () => {
      window.removeEventListener("scroll", updateActiveSection);
      window.removeEventListener("resize", updateActiveSection);
    };
  }, []);

  function slugify(value: string) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 100);
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
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
        whatsapp_number: form.get("whatsapp_number") || null,
        address: form.get("address") || null,
        timezone: form.get("timezone"),
        allow_staff_selection: form.get("allow_staff_selection") === "on",
        advance_booking_days: Number(form.get("advance_booking_days")),
        default_deposit_amount: ngnToKobo(form.get("default_deposit_amount")),
        min_notice_hours: Number(form.get("min_notice_hours")),
        cancellation_notice_hours: Number(form.get("cancellation_notice_hours")),
        front_desk_intro: form.get("front_desk_intro") || null,
        front_desk_hours: form.get("front_desk_hours") || null,
        front_desk_service_areas: form.get("front_desk_service_areas") || null,
        front_desk_prep_notes: form.get("front_desk_prep_notes") || null,
        front_desk_policies: form.get("front_desk_policies") || null,
        front_desk_escalation_rules: form.get("front_desk_escalation_rules") || null,
      });
      setTenant(updated);
      setSlugDraft(updated.slug);
      setMessage("Settings saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save settings");
    }
  }

  async function savePayoutSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setPayoutWarning("");
    const form = new FormData(event.currentTarget);
    const status = await api.savePayoutSetup({
      account_name: form.get("account_name") || null,
      bank_name: form.get("bank_name"),
      account_number: form.get("account_number"),
    });
    setPaymentStatus(status);
    setTenant((current) =>
      current
        ? {
            ...current,
            payout_bank_name: status.payout_bank_name,
            payout_account_name: status.payout_account_name,
            payment_setup_status: status.payment_setup_status,
          }
        : current,
    );
    if (status.warning_message) {
      setPayoutWarning(status.warning_message);
    }
    if (status.payout_ready) {
      setMessage("Payout account saved");
    }
  }

  // Backend handles account verification automatically when payout details are saved.

  const publicBookingUrl = `${publicOrigin}/book/${slugDraft || tenant?.slug || ""}`;

  return (
    <DashboardShell title="Settings">
      <section className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="bookie-card hidden h-fit p-4 lg:sticky lg:top-6 lg:block">
          <h2 className="section-title">Settings</h2>
          <nav className="mt-4 grid gap-1">
            {sectionLinks.map(([label, id]) => (
              <a
                key={id}
                href={`#${id}`}
                aria-current={activeSection === id ? "true" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  setActiveSection(id);
                  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
                  history.replaceState(null, "", `#${id}`);
                }}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  activeSection === id ? "bg-[#e8efe9] text-[#0e4731] shadow-inner" : "text-[#556e61] hover:bg-[#e8efe9] hover:text-[#0e4731]"
                }`}
              >
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="grid gap-6">
          <form onSubmit={saveSettings} className="grid gap-6">
            <section id="booking-link" className="bookie-card scroll-mt-8 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="section-title">Booking link</h2>
                  <p className="bookie-subtitle mt-1">Share this link anywhere clients should book.</p>
                </div>
                <button type="button" className="secondary-button min-h-0 rounded-xl px-4 py-2 text-sm" onClick={() => setSlugDraft(slugify(tenant?.name || "bookie-business"))}>
                  Generate
                </button>
              </div>
              <div className="mt-5 grid gap-3 lg:grid-cols-[auto_1fr_auto] lg:items-end">
                <label className="bookie-label">
                  Base
                  <input readOnly value={`${publicOrigin}/book/`} className="bg-white text-[#556e61]" />
                </label>
                <label className="bookie-label">
                  Custom link name
                  <input name="slug" value={slugDraft} onChange={(event) => setSlugDraft(slugify(event.target.value))} placeholder="studio-ayo" required />
                </label>
                <button className="secondary-button" type="button" onClick={async () => { await navigator.clipboard?.writeText(publicBookingUrl); setMessage("Booking link copied"); }} disabled={!slugDraft}>
                  Copy link
                </button>
              </div>
              <a className="mt-3 block break-all text-sm font-semibold text-[#0e4731] underline-offset-4 hover:underline" href={publicBookingUrl} target="_blank" rel="noreferrer">
                {publicBookingUrl}
              </a>
            </section>

            <section id="business-details" className="bookie-card scroll-mt-8 p-5">
              <h2 className="section-title">Business details</h2>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className="bookie-label">Business name<input name="name" placeholder="Le'Test Beauty Salon" defaultValue={tenant?.name ?? ""} required /></label>
                <label className="bookie-label">Timezone<input name="timezone" placeholder="Africa/Lagos" defaultValue={tenant?.timezone ?? "Africa/Lagos"} required /></label>
                <label className="bookie-label">Phone<input name="phone" placeholder="+234..." defaultValue={tenant?.phone ?? ""} /></label>
                <label className="bookie-label">WhatsApp number<input name="whatsapp_number" placeholder="+234..." defaultValue={tenant?.whatsapp_number ?? ""} /></label>
                <label className="bookie-label">Address<input name="address" placeholder="Business address" defaultValue={tenant?.address ?? ""} /></label>
                <label className="bookie-label sm:col-span-2">What clients should know<textarea name="description" placeholder="Short description clients will see on your booking page." defaultValue={tenant?.description ?? ""} /></label>
              </div>
            </section>

            <section id="booking-rules" className="bookie-card scroll-mt-8 p-5">
              <h2 className="section-title">Booking rules</h2>
              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <label className="bookie-label">How far ahead clients can book<input name="advance_booking_days" type="number" min={1} defaultValue={tenant?.advance_booking_days ?? 30} /></label>
                <label className="bookie-label">Minimum notice before booking<input name="min_notice_hours" type="number" min={0} defaultValue={tenant?.min_notice_hours ?? 2} /></label>
                <label className="bookie-label">Minimum notice before cancel<input name="cancellation_notice_hours" type="number" min={0} defaultValue={tenant?.cancellation_notice_hours ?? 24} /></label>
              </div>
              <label className="mt-5 flex items-center gap-3 text-sm font-semibold text-[#0f2119]">
                <input className="h-4 min-h-0 w-4 accent-[#0e4731]" name="allow_staff_selection" type="checkbox" defaultChecked={tenant?.allow_staff_selection ?? true} />
                Let clients choose staff
              </label>
            </section>

            <section id="whatsapp-front-desk" className="bookie-card scroll-mt-8 p-5">
              <h2 className="section-title">WhatsApp front desk</h2>
              <p className="bookie-subtitle mt-1">These notes guide the WhatsApp booking desk and the human handoff flow.</p>
              <div className="mt-5 grid gap-4">
                <label className="bookie-label">Front desk intro<textarea name="front_desk_intro" placeholder="Short greeting or brand voice for the WhatsApp desk." defaultValue={tenant?.front_desk_intro ?? ""} /></label>
                <label className="bookie-label">Hours and availability<textarea name="front_desk_hours" placeholder="Working hours, off days, response windows." defaultValue={tenant?.front_desk_hours ?? ""} /></label>
                <label className="bookie-label">Service areas<textarea name="front_desk_service_areas" placeholder="Which areas you serve, branches, or travel zones." defaultValue={tenant?.front_desk_service_areas ?? ""} /></label>
                <label className="bookie-label">Preparation notes<textarea name="front_desk_prep_notes" placeholder="What customers should prepare before arriving or booking." defaultValue={tenant?.front_desk_prep_notes ?? ""} /></label>
                <label className="bookie-label">Policies<textarea name="front_desk_policies" placeholder="Cancellation, deposit, late arrival, or other policy text." defaultValue={tenant?.front_desk_policies ?? ""} /></label>
                <label className="bookie-label">Escalation rules<textarea name="front_desk_escalation_rules" placeholder="When the bot should hand off to a human." defaultValue={tenant?.front_desk_escalation_rules ?? ""} /></label>
              </div>
            </section>

            <section id="deposits" className="bookie-card scroll-mt-8 p-5">
              <h2 className="section-title">Deposits</h2>
              <p className="bookie-subtitle mt-1">This is the normal amount clients pay to hold a booking.</p>
              <label className="bookie-label mt-5 max-w-md">
                Normal deposit amount (NGN)
                <input name="default_deposit_amount" type="number" min={0} step={1} placeholder="25000" defaultValue={koboToNgn(tenant?.default_deposit_amount)} />
                <span className="bookie-help">Example: 25000 means ₦25,000.</span>
              </label>
              <button className="mt-5" type="submit">Save settings</button>
            </section>
          </form>

          <section id="payments" className="bookie-card scroll-mt-8 p-5">
            <h2 className="section-title">Payments</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-[#0e4731]/15 bg-[#e8efe9] p-4">
                <span className="status-badge status-badge-success">On</span>
                <h3 className="mt-3 text-lg font-semibold text-[#0f2119]">Deposits are turned on</h3>
                <p className="bookie-subtitle mt-1">Customers can pay through your booking link.</p>
              </div>
              <div className="rounded-2xl border border-slate-100 bg-white p-4">
                <span className="status-badge">{paymentStatus?.payout_ready ? "Saved" : "Needed"}</span>
                <h3 className="mt-3 text-lg font-semibold text-[#0f2119]">
                  {paymentStatus?.payout_ready ? "Payout account saved" : "Payout account needed"}
                </h3>
                <p className="bookie-subtitle mt-1">
                  {paymentStatus?.payout_ready
                    ? "Money from paid bookings will be sent to your saved account."
                    : "Add the bank account where you want to receive your money."}
                </p>
              </div>
            </div>
          </section>

          <section id="payout-account" className="bookie-card scroll-mt-8 p-5">
            <h2 className="section-title">Payout account</h2>
            <p className="bookie-subtitle mt-1">
              This is the bank account where Bookie will send money from your paid bookings.
            </p>

            {paymentStatus?.payout_ready && paymentStatus?.payout_account_name ? (
              <div className="mt-5 rounded-2xl border border-[#0e4731]/15 bg-[#e8efe9] p-5">
                <h3 className="text-lg font-semibold text-[#0f2119]">Payout account saved</h3>
                <p className="bookie-subtitle mt-1">
                  Money from paid bookings will be sent to:
                </p>
                <div className="mt-4 space-y-1 text-sm font-semibold text-[#0f2119]">
                  <p>{paymentStatus.payout_account_name}</p>
                  <p>{paymentStatus.payout_bank_name}</p>
                  <p>{paymentStatus.masked_payout_account_number}</p>
                </div>
                <button
                  type="button"
                  className="mt-4 secondary-button text-sm"
                  onClick={() => {
                    setPaymentStatus((prev) => prev ? { ...prev, payout_ready: false } : null);
                    setPayoutWarning("");
                  }}
                >
                  Edit payout account
                </button>
              </div>
            ) : (
              <form onSubmit={savePayoutSetup} className="mt-5 grid gap-4 sm:grid-cols-[1fr_1fr_1fr_auto] sm:items-end">
                <label className="bookie-label">
                  Account name
                  <input
                    name="account_name"
                    placeholder="Account holder name"
                    defaultValue={paymentStatus?.payout_account_name ?? tenant?.payout_account_name ?? tenant?.name ?? ""}
                  />
                </label>
                <label className="bookie-label">
                  Bank
                  <input
                    name="bank_name"
                    placeholder="GTBank, Access Bank, Zenith..."
                    defaultValue={paymentStatus?.payout_bank_name ?? tenant?.payout_bank_name ?? ""}
                    required
                  />
                </label>
                <label className="bookie-label">
                  Account number
                  <input
                    name="account_number"
                    placeholder="10-digit account number"
                    required
                  />
                </label>
                <button type="submit">Save payout account</button>
              </form>
            )}
          </section>

          {message && <p className="rounded-xl border border-[#0e4731]/15 bg-[#e8efe9] px-4 py-3 text-sm font-semibold text-[#0e4731]">{message}</p>}
          {payoutWarning && <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">{payoutWarning}</p>}
          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
        </div>
      </section>
    </DashboardShell>
  );
}
