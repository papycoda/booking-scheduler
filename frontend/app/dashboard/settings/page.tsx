"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Tenant } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

export default function SettingsPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.currentTenant().then(setTenant).catch((err) => setError(err.message));
  }, []);

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const updated = await api.updateTenant({
      name: form.get("name"),
      description: form.get("description") || null,
      phone: form.get("phone") || null,
      address: form.get("address") || null,
      timezone: form.get("timezone"),
      allow_staff_selection: form.get("allow_staff_selection") === "on",
      advance_booking_days: Number(form.get("advance_booking_days")),
      default_deposit_amount: Number(form.get("default_deposit_amount")),
      min_notice_hours: Number(form.get("min_notice_hours")),
      cancellation_notice_hours: Number(form.get("cancellation_notice_hours")),
    });
    setTenant(updated);
    setMessage("Settings saved");
  }

  async function onboardPaystack(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.onboardPaystack({
      business_name: form.get("business_name"),
      settlement_bank: form.get("settlement_bank"),
      account_number: form.get("account_number"),
    });
    setMessage("Paystack onboarding submitted");
  }

  return (
    <DashboardShell title="Settings">
      <form onSubmit={saveSettings} className="grid gap-3 border border-line bg-white p-4 sm:grid-cols-2">
        <input name="name" placeholder="Business name" defaultValue={tenant?.name ?? ""} required />
        <input name="timezone" placeholder="Timezone" defaultValue={tenant?.timezone ?? "Africa/Lagos"} required />
        <input name="phone" placeholder="Phone" defaultValue={tenant?.phone ?? ""} />
        <input name="address" placeholder="Address" defaultValue={tenant?.address ?? ""} />
        <input name="advance_booking_days" type="number" min={1} defaultValue={tenant?.advance_booking_days ?? 30} />
        <input name="default_deposit_amount" type="number" min={0} placeholder="Default deposit in kobo" defaultValue={tenant?.default_deposit_amount ?? 0} />
        <input name="min_notice_hours" type="number" min={0} defaultValue={tenant?.min_notice_hours ?? 2} />
        <input name="cancellation_notice_hours" type="number" min={0} defaultValue={tenant?.cancellation_notice_hours ?? 24} />
        <label className="flex items-center gap-2 text-sm"><input className="w-auto" name="allow_staff_selection" type="checkbox" defaultChecked={tenant?.allow_staff_selection ?? true} />Allow staff selection</label>
        <textarea name="description" placeholder="Description" defaultValue={tenant?.description ?? ""} />
        <button type="submit">Save Settings</button>
      </form>
      <form onSubmit={onboardPaystack} className="grid gap-3 border border-line bg-white p-4 sm:grid-cols-4">
        <input name="business_name" placeholder="Paystack business name" defaultValue={tenant?.name ?? ""} required />
        <input name="settlement_bank" placeholder="Bank code" required />
        <input name="account_number" placeholder="Account number" required />
        <button type="submit">Connect Paystack</button>
      </form>
      {message && <p className="text-sm text-action">{message}</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
