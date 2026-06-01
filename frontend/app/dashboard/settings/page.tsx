"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, koboToNgn, ngnToKobo, PaymentSetupStatus, Tenant } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

export default function SettingsPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<PaymentSetupStatus | null>(null);
  const [slugDraft, setSlugDraft] = useState("");
  const [publicOrigin, setPublicOrigin] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setPublicOrigin(window.location.origin);
    Promise.all([api.currentTenant(), api.paystackStatus()])
      .then(([tenantRow, status]) => {
        setTenant(tenantRow);
        setSlugDraft(tenantRow.slug);
        setPaymentStatus(status);
      })
      .catch((err) => setError(err.message));
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
        address: form.get("address") || null,
        timezone: form.get("timezone"),
        allow_staff_selection: form.get("allow_staff_selection") === "on",
        advance_booking_days: Number(form.get("advance_booking_days")),
        default_deposit_amount: ngnToKobo(form.get("default_deposit_amount")),
        min_notice_hours: Number(form.get("min_notice_hours")),
        cancellation_notice_hours: Number(form.get("cancellation_notice_hours")),
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
    const form = new FormData(event.currentTarget);
    const status = await api.savePayoutSetup({
      account_name: form.get("account_name") || null,
      bank_code: form.get("bank_code"),
      account_number: form.get("account_number"),
    });
    setPaymentStatus(status);
    setTenant((current) =>
      current
        ? {
            ...current,
            payout_bank_code: status.payout_bank_code,
            payout_account_number: status.payout_account_number,
            payout_account_name: status.payout_account_name,
            payout_recipient_code: status.payout_recipient_code,
            payment_setup_status: status.payment_setup_status,
          }
        : current,
    );
    setMessage(status.payout_recipient_code ? "Payout details saved" : "Bank details saved. Recipient verification can be retried later.");
  }

  async function onboardPaystack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const status = await api.onboardPaystack({
      business_name: form.get("business_name"),
      settlement_bank: form.get("settlement_bank"),
      account_number: form.get("account_number"),
    });
    setPaymentStatus(status);
    setTenant((current) =>
      current
        ? {
            ...current,
            paystack_subaccount_code: status.paystack_subaccount_code,
            paystack_business_name: status.paystack_business_name,
            payout_bank_code: status.payout_bank_code,
            payout_account_number: status.payout_account_number,
            payout_account_name: status.payout_account_name,
            payment_setup_status: status.payment_setup_status,
          }
        : current,
    );
    setMessage("Direct split settlement connected");
  }

  const setupStatus = paymentStatus?.payment_setup_status ?? tenant?.payment_setup_status ?? "not_started";
  const publicBookingUrl = `${publicOrigin}/book/${slugDraft || tenant?.slug || ""}`;
  const payoutStatusCopy =
    setupStatus === "split_ready"
      ? "Direct split ready. Future checkout payments can route business funds directly."
      : setupStatus === "bank_added"
        ? "Payout details saved. Platform-collected booking payments can be settled to this account."
        : "Payout setup pending. Clients can still pay deposits now; business payouts wait until bank details are added.";

  return (
    <DashboardShell title="Settings">
      <section className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <aside className="dashboard-card hidden h-fit p-4 lg:sticky lg:top-6 lg:block">
          <p className="eyebrow">Settings</p>
          <nav className="mt-4 grid gap-1">
            {[
              ["Booking link", "#booking-link"],
              ["Business profile", "#business-profile"],
              ["Payments", "#payments"],
              ["Payout account", "#payout-account"],
              ["Direct split", "#direct-split"],
            ].map(([label, href]) => (
              <a key={href} href={href} className="rounded-xl px-3 py-2 text-sm font-semibold text-ink/65 transition hover:bg-field hover:text-action">
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="grid gap-6">
      <form id="business-profile" onSubmit={saveSettings} className="dashboard-card grid gap-5 p-5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <p className="eyebrow">Business profile</p>
          <h2 className="section-title">Booking rules and display details</h2>
        </div>
        <section id="booking-link" className="grid gap-3 rounded-2xl border border-line/70 bg-[#fcfdfe] p-4 sm:col-span-2">
          <div>
            <p className="eyebrow">Public booking link</p>
            <h3 className="font-semibold text-ink">Custom URL</h3>
          </div>
          <div className="grid gap-3 lg:grid-cols-[auto_1fr_auto_auto] lg:items-end">
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Base
              <input readOnly value={`${publicOrigin}/book/`} className="bg-white text-ink/55" />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Slug
              <input
                name="slug"
                value={slugDraft}
                onChange={(event) => setSlugDraft(slugify(event.target.value))}
                placeholder="studio-ayo"
                required
              />
            </label>
            <button
              className="secondary-button self-end"
              type="button"
              onClick={() => setSlugDraft(slugify(tenant?.name || "bookie-business"))}
            >
              Generate
            </button>
            <button
              className="secondary-button self-end"
              type="button"
              onClick={async () => {
                await navigator.clipboard?.writeText(publicBookingUrl);
                setMessage("Booking link copied");
              }}
              disabled={!slugDraft}
            >
              Copy link
            </button>
          </div>
          <a className="text-sm font-semibold text-action underline-offset-4 hover:underline" href={publicBookingUrl} target="_blank" rel="noreferrer">
            {publicBookingUrl}
          </a>
          <p className="muted">This is the link clients use to book without creating an account.</p>
        </section>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Business name
          <input name="name" placeholder="Le'Test" defaultValue={tenant?.name ?? ""} required />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Timezone
          <input name="timezone" placeholder="Africa/Lagos" defaultValue={tenant?.timezone ?? "Africa/Lagos"} required />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Phone
          <input name="phone" placeholder="+234..." defaultValue={tenant?.phone ?? ""} />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Address
          <input name="address" placeholder="Business address" defaultValue={tenant?.address ?? ""} />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Advance booking window
          <input name="advance_booking_days" type="number" min={1} defaultValue={tenant?.advance_booking_days ?? 30} />
          <span className="text-xs font-normal text-ink/55">How many days ahead clients can book.</span>
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Default deposit amount (NGN)
          <input name="default_deposit_amount" type="number" min={0} step={1} placeholder="25000" defaultValue={koboToNgn(tenant?.default_deposit_amount)} />
          <span className="text-xs font-normal text-ink/55">Enter the naira amount clients pay now. Example: 25000 = NGN 25,000.</span>
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Minimum notice
          <input name="min_notice_hours" type="number" min={0} defaultValue={tenant?.min_notice_hours ?? 2} />
          <span className="text-xs font-normal text-ink/55">Minimum hours before a client can book.</span>
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Cancellation notice
          <input name="cancellation_notice_hours" type="number" min={0} defaultValue={tenant?.cancellation_notice_hours ?? 24} />
          <span className="text-xs font-normal text-ink/55">Minimum hours required before cancellation.</span>
        </label>
        <label className="flex items-center gap-2 text-sm font-semibold text-ink/75">
          <input className="w-auto" name="allow_staff_selection" type="checkbox" defaultChecked={tenant?.allow_staff_selection ?? true} />
          Allow staff selection
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Public description
          <textarea name="description" placeholder="Short description clients will see on your booking page." defaultValue={tenant?.description ?? ""} />
        </label>
        <button type="submit">Save Settings</button>
      </form>
      <section id="payments" className="dashboard-card grid gap-4 p-5">
        <div>
          <p className="eyebrow">Payments</p>
          <h2 className="section-title">Collection and payout status</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="metric">
            <strong>Active</strong>
            <span className="muted">Payments can be collected now</span>
          </div>
          <div className="metric">
            <strong>{setupStatus.replace("_", " ")}</strong>
            <span className="muted">Payout setup</span>
          </div>
          <div className="metric">
            <strong>{paymentStatus?.payout_ready ? "Ready" : "Pending"}</strong>
            <span className="muted">Business payouts</span>
          </div>
        </div>
        <p className="muted">{payoutStatusCopy}</p>
      </section>
      <form id="payout-account" onSubmit={savePayoutSetup} className="finance-card grid gap-4 sm:grid-cols-4">
        <div className="sm:col-span-4">
          <p className="eyebrow">Payout account</p>
          <h2 className="section-title">Add bank details without Paystack setup</h2>
        </div>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Account name
          <input name="account_name" placeholder="Registered account name" defaultValue={tenant?.payout_account_name ?? tenant?.name ?? ""} />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Bank code
          <input name="bank_code" placeholder="Example: 058" defaultValue={tenant?.payout_bank_code ?? ""} required />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Account number
          <input name="account_number" placeholder="10-digit account number" defaultValue={tenant?.payout_account_number ?? ""} required />
        </label>
        <button type="submit">Save payout account</button>
      </form>
      <form id="direct-split" onSubmit={onboardPaystack} className="finance-card grid gap-4 sm:grid-cols-4">
        <div className="sm:col-span-4">
          <p className="eyebrow">Payments</p>
          <h2 className="section-title">Optional direct split settlement</h2>
        </div>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Paystack business name
          <input name="business_name" placeholder="Registered business name" defaultValue={tenant?.name ?? ""} required />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Bank code
          <input name="settlement_bank" placeholder="Example: 058" required />
        </label>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Account number
          <input name="account_number" placeholder="10-digit account number" required />
        </label>
        <button type="submit">Connect Paystack</button>
      </form>
      {message && <p className="text-sm text-action">{message}</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}
        </div>
      </section>
    </DashboardShell>
  );
}
