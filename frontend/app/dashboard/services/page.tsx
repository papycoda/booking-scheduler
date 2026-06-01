"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatNgn, ngnToKobo, Service } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setServices(await api.dashboardServices());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load services");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createService({
      name: form.get("name"),
      description: form.get("description") || null,
      duration_minutes: Number(form.get("duration_minutes")),
      price: ngnToKobo(form.get("price")),
      currency: "NGN",
      pricing_mode: form.get("pricing_mode"),
      deposit_policy: form.get("deposit_policy"),
      deposit_amount: form.get("deposit_amount") ? ngnToKobo(form.get("deposit_amount")) : null,
    });
    event.currentTarget.reset();
    await load();
  }

  return (
    <DashboardShell title="Services">
      <form onSubmit={submit} className="panel grid gap-3 sm:grid-cols-4">
        <div className="sm:col-span-4">
          <p className="eyebrow">Service catalog</p>
          <h2 className="section-title">Add a bookable service</h2>
        </div>
        <input name="name" placeholder="Service name" required />
        <input name="duration_minutes" type="number" min={5} max={480} placeholder="Duration" required />
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Base/from price (NGN)
          <input name="price" type="number" min={0} step={1} placeholder="25000" required />
        </label>
        <select name="pricing_mode" defaultValue="fixed">
          <option value="fixed">Fixed price</option>
          <option value="from">From price</option>
          <option value="consultation">Consultation price</option>
        </select>
        <select name="deposit_policy" defaultValue="tenant_default">
          <option value="tenant_default">Use default deposit</option>
          <option value="custom">Custom deposit</option>
          <option value="disabled">Full price now</option>
        </select>
        <label className="grid gap-2 text-sm font-semibold text-ink/75">
          Custom deposit (NGN)
          <input name="deposit_amount" type="number" min={0} step={1} placeholder="5000" />
        </label>
        <input name="description" placeholder="Description" />
        <button type="submit">Add Service</button>
      </form>
      <section className="grid gap-3">
        {services.map((service) => (
          <div key={service.id} className="panel flex items-center justify-between gap-4">
            <div>
              <strong>{service.name}</strong>
              <p className="text-sm text-ink/70">
                {service.duration_minutes} min - {service.pricing_mode === "consultation" ? "Price by consultation" : formatNgn(service.price)}
              </p>
              <p className="text-xs text-ink/60">
                Deposit: {service.deposit_policy === "custom" ? formatNgn(service.deposit_amount) : service.deposit_policy === "tenant_default" ? "Business default" : "Full fixed price"}
              </p>
            </div>
            <button className="secondary-button" type="button" onClick={async () => { await api.deleteService(service.id); await load(); }}>Deactivate</button>
          </div>
        ))}
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
