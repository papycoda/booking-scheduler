"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatNgn, koboToNgn, ngnToKobo, Service } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const pricingModes = [
  { value: "fixed", label: "Fixed Price", hint: "Charge a clear listed price." },
  { value: "from", label: "Variable", hint: "Show a starting price." },
  { value: "consultation", label: "Consultation", hint: "Quote after review." },
] as const;

const depositPolicies = [
  { value: "tenant_default", label: "Default deposit", hint: "Use business profile amount." },
  { value: "custom", label: "Custom deposit", hint: "Set this service's deposit." },
  { value: "disabled", label: "Full price now", hint: "Only for fixed-price services." },
] as const;

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [pricingMode, setPricingMode] = useState<Service["pricing_mode"]>("fixed");
  const [depositPolicy, setDepositPolicy] = useState<Service["deposit_policy"]>("tenant_default");
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState("");
  const selectedService = services.find((service) => service.id === selectedId);

  async function load() {
    try {
      const rows = await api.dashboardServices();
      setServices(rows);
      if (!selectedId && rows[0]) {
        selectService(rows[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load services");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function selectService(service: Service) {
    setSelectedId(service.id);
    setPricingMode(service.pricing_mode);
    setDepositPolicy(service.deposit_policy);
    setIsActive(service.is_active);
  }

  function startNewService() {
    setSelectedId("");
    setPricingMode("fixed");
    setDepositPolicy("tenant_default");
    setIsActive(true);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const body = {
      name: form.get("name"),
      description: form.get("description") || null,
      duration_minutes: Number(form.get("duration_minutes")),
      price: ngnToKobo(form.get("price")),
      currency: "NGN",
      pricing_mode: pricingMode,
      deposit_policy: depositPolicy,
      deposit_amount: form.get("deposit_amount") ? ngnToKobo(form.get("deposit_amount")) : null,
      is_active: isActive,
    };
    try {
      if (selectedService) {
        await api.updateService(selectedService.id, body);
      } else {
        await api.createService(body);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save service");
    }
  }

  return (
    <DashboardShell title="Services">
      <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="dashboard-card p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Service catalog</p>
              <h2 className="section-title">Bookable services</h2>
            </div>
            <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={startNewService}>
              New
            </button>
          </div>
          <div className="grid gap-3">
            {services.map((service) => (
              <button
                key={service.id}
                type="button"
                onClick={() => selectService(service)}
                className={[
                  "grid min-h-0 gap-2 rounded-2xl border p-4 text-left shadow-none",
                  selectedId === service.id ? "border-action bg-action/5" : "border-line/70 bg-[#fcfdfe]",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <strong className="text-sm text-ink">{service.name}</strong>
                  <span className={service.is_active ? "status-badge status-badge-success" : "status-badge status-badge-muted"}>
                    {service.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="text-xs font-medium text-ink/65">
                  {service.duration_minutes} min - {service.pricing_mode === "consultation" ? "Consultation quote" : formatNgn(service.price)}
                </p>
                <p className="text-xs text-ink/55">
                  Deposit: {service.deposit_policy === "custom" ? formatNgn(service.deposit_amount) : service.deposit_policy === "tenant_default" ? "Business default" : "Full fixed price"}
                </p>
              </button>
            ))}
            {services.length === 0 && <p className="muted">No services yet.</p>}
          </div>
        </aside>

        <form key={selectedService?.id ?? "new"} onSubmit={submit} className="dashboard-card grid gap-5 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Configuration</p>
              <h2 className="section-title">{selectedService ? "Edit service" : "Create service"}</h2>
            </div>
            <label className="flex items-center gap-3 text-xs font-bold uppercase tracking-wider text-ink/60">
              Active
              <input className="sr-only" type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
              <span className="switch-track" data-active={isActive}>
                <span className="switch-thumb" />
              </span>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Service name
              <input name="name" placeholder="Premium install" defaultValue={selectedService?.name ?? ""} required />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Duration minutes
              <input name="duration_minutes" type="number" min={5} max={480} placeholder="90" defaultValue={selectedService?.duration_minutes ?? 60} required />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Base/from price (NGN)
              <input name="price" type="number" min={0} step={1} placeholder="25000" defaultValue={koboToNgn(selectedService?.price)} required />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-ink/75">
              Custom deposit (NGN)
              <input name="deposit_amount" type="number" min={0} step={1} placeholder="5000" defaultValue={koboToNgn(selectedService?.deposit_amount)} />
            </label>
          </div>

          <section className="grid gap-3">
            <p className="text-sm font-bold text-ink">Pricing mode</p>
            <div className="grid gap-2 sm:grid-cols-3">
              {pricingModes.map((mode) => (
                <label key={mode.value} className="segmented-option border border-line/70 bg-white p-3" data-active={pricingMode === mode.value}>
                  <input className="sr-only" type="radio" name="pricing_mode" value={mode.value} checked={pricingMode === mode.value} onChange={() => setPricingMode(mode.value)} />
                  <span className="block">{mode.label}</span>
                  <span className="mt-1 block text-[11px] font-medium opacity-70">{mode.hint}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="grid gap-3">
            <p className="text-sm font-bold text-ink">Deposit rule</p>
            <div className="grid gap-2 sm:grid-cols-3">
              {depositPolicies.map((policy) => (
                <label key={policy.value} className="segmented-option border border-line/70 bg-white p-3" data-active={depositPolicy === policy.value}>
                  <input className="sr-only" type="radio" name="deposit_policy" value={policy.value} checked={depositPolicy === policy.value} onChange={() => setDepositPolicy(policy.value)} />
                  <span className="block">{policy.label}</span>
                  <span className="mt-1 block text-[11px] font-medium opacity-70">{policy.hint}</span>
                </label>
              ))}
            </div>
          </section>

          <label className="grid gap-2 text-sm font-semibold text-ink/75">
            Description
            <textarea name="description" placeholder="What clients should know before booking." defaultValue={selectedService?.description ?? ""} />
          </label>

          <div className="flex flex-wrap gap-3">
            <button type="submit">{selectedService ? "Save service" : "Add service"}</button>
            {selectedService && (
              <button className="danger-link" type="button" onClick={async () => { await api.deleteService(selectedService.id); startNewService(); await load(); }}>
                Deactivate
              </button>
            )}
          </div>
          {error && <p className="text-sm text-red-700">{error}</p>}
        </form>
      </section>
    </DashboardShell>
  );
}
