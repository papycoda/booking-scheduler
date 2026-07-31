"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, depositPolicyLabel, formatNgn, koboToNgn, ngnToKobo, priceModeLabel, Service } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const priceChoices = [
  { value: "fixed", label: "Fixed price", hint: "The price is clear before booking." },
  { value: "from", label: "Starts from", hint: "Show a starting price and quote later." },
  { value: "consultation", label: "Quote after details", hint: "Use notes or inspo before final price." },
] as const;

const payNowChoices = [
  { value: "tenant_default", label: "Use my normal deposit", hint: "Use the deposit set in settings." },
  { value: "custom", label: "Set a different deposit", hint: "Choose a deposit for this service only." },
  { value: "disabled", label: "Take full payment now", hint: "Use only when the price is fixed." },
] as const;

function EditIcon() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
    </svg>
  );
}

function DeleteIcon() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [deletingService, setDeletingService] = useState<Service | null>(null);
  const [pricingMode, setPricingMode] = useState<Service["pricing_mode"]>("fixed");
  const [depositPolicy, setDepositPolicy] = useState<Service["deposit_policy"]>("tenant_default");
  const [isActive, setIsActive] = useState(true);
  const [priceDraft, setPriceDraft] = useState("25000");
  const [depositDraft, setDepositDraft] = useState("");
  const [nameDraft, setNameDraft] = useState("");
  const [durationDraft, setDurationDraft] = useState("60");
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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

  function openNewModal() {
    setEditingService(null);
    setPricingMode("fixed");
    setDepositPolicy("tenant_default");
    setIsActive(true);
    setPriceDraft("25000");
    setDepositDraft("");
    setNameDraft("");
    setDurationDraft("60");
    setDescriptionDraft("");
    setError("");
    setMessage("");
    setEditModalOpen(true);
  }

  function openEditModal(service: Service) {
    setEditingService(service);
    setPricingMode(service.pricing_mode);
    setDepositPolicy(service.deposit_policy);
    setIsActive(service.is_active);
    setPriceDraft(String(koboToNgn(service.price)));
    setDepositDraft(service.deposit_amount ? String(koboToNgn(service.deposit_amount)) : "");
    setNameDraft(service.name);
    setDurationDraft(String(service.duration_minutes));
    setDescriptionDraft(service.description ?? "");
    setError("");
    setMessage("");
    setEditModalOpen(true);
  }

  function closeEditModal() {
    setEditModalOpen(false);
    setEditingService(null);
  }

  function openDeleteConfirm(service: Service) {
    setDeletingService(service);
    setDeleteConfirmOpen(true);
  }

  function closeDeleteConfirm() {
    setDeleteConfirmOpen(false);
    setDeletingService(null);
  }

  async function handleDelete() {
    if (!deletingService) return;
    try {
      await api.deleteService(deletingService.id);
      setServices((current) => current.filter((service) => service.id !== deletingService.id));
      closeDeleteConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete service");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const body = {
      name: nameDraft,
      description: descriptionDraft || null,
      duration_minutes: Number(durationDraft),
      price: ngnToKobo(priceDraft),
      currency: "NGN",
      pricing_mode: pricingMode,
      deposit_policy: depositPolicy,
      deposit_amount: depositDraft ? ngnToKobo(depositDraft) : null,
      is_active: isActive,
    };
    try {
      if (editingService) {
        const updated = await api.updateService(editingService.id, body);
        setServices((current) => current.map((service) => (service.id === editingService.id ? updated : service)));
        setMessage("Service saved");
      } else {
        const created = await api.createService(body);
        setServices((current) => [...current, created]);
        setMessage("Service added");
      }
      window.setTimeout(closeEditModal, 450);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save service");
    }
  }

  const previewPrice = ngnToKobo(priceDraft);
  const previewDeposit = depositPolicy === "custom" && depositDraft ? ngnToKobo(depositDraft) : null;
  const previewPriceText = pricingMode === "consultation" ? "Quote after details" : `${pricingMode === "from" ? "Starts from " : ""}${formatNgn(previewPrice)}`;
  const previewPayNowText =
    depositPolicy === "disabled"
      ? "Full payment now"
      : previewDeposit
        ? `${formatNgn(previewDeposit)} deposit`
        : "Normal deposit";

  return (
    <DashboardShell title="Services">
      <section className="bookie-card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5 sm:p-6">
          <div>
            <span className="inline-flex rounded-md border border-[#0e4731]/10 bg-[#e8efe9] px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-[#0e4731]">
              Service menu
            </span>
            <h1 className="mt-4 text-2xl font-semibold tracking-normal text-[#0f2119]">Services & pricing</h1>
            <p className="bookie-subtitle mt-2">Set up what clients can book, how long it takes, and what they pay.</p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-sm shadow-[0_14px_30px_rgba(14,71,49,0.18)]" type="button" onClick={openNewModal}>
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
            </svg>
            Add new service
          </button>
        </div>

        <div className="grid gap-3 p-5 sm:p-6">
          {services.map((service) => (
            <div key={service.id} className="service-menu-row">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <strong className="text-base text-[#0f2119]">{service.name}</strong>
                  <span className="rounded-md border border-[#0e4731]/10 bg-[#e8efe9] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em] text-[#0e4731]">
                    {service.is_active ? "On" : "Off"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm font-medium text-[#556e61]">
                  <span>{service.duration_minutes} min</span>
                  <span className="h-1 w-1 rounded-full bg-slate-300" />
                  <span>{priceModeLabel(service.pricing_mode)}</span>
                  <span className="h-1 w-1 rounded-full bg-slate-300" />
                  <span>{depositPolicyLabel(service.deposit_policy)}</span>
                </div>
              </div>

              <div className="flex items-center gap-3 sm:justify-end">
                <button type="button" onClick={() => openEditModal(service)} className="icon-button edit" aria-label={`Edit ${service.name}`} title="Edit service">
                  <EditIcon />
                </button>
                <button type="button" onClick={() => openDeleteConfirm(service)} className="icon-button danger" aria-label={`Delete ${service.name}`} title="Delete service">
                  <DeleteIcon />
                </button>
              </div>
            </div>
          ))}
          {services.length === 0 && <p className="soft-empty">No services yet. Add the first one here.</p>}
        </div>
      </section>

      {editModalOpen && (
        <div className="modal-overlay" onClick={closeEditModal}>
          <div className="modal-content modal-content-wide" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-[#0f2119]">{editingService ? "Edit service" : "Add service"}</h1>
                <p className="bookie-subtitle mt-1">Make the offer clear before clients choose a time.</p>
              </div>
              <button type="button" onClick={closeEditModal} className="icon-button" aria-label="Close">
                <CloseIcon />
              </button>
            </div>

            <form onSubmit={submit}>
              <div className="modal-body grid gap-6 lg:grid-cols-[1fr_300px]">
                <div className="grid gap-5">
                  <label className="flex items-center gap-3 text-sm font-semibold text-[#556e61]">
                    Booking is {isActive ? "on" : "off"}
                    <input className="sr-only" type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
                    <span className="switch-track" data-active={isActive}><span className="switch-thumb" /></span>
                  </label>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="bookie-label">
                      Service name
                      <input name="name" placeholder="Brow shaping and tint" value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} required />
                    </label>
                    <label className="bookie-label">
                      How long it takes (minutes)
                      <input name="duration_minutes" type="number" min={5} max={480} step={5} value={durationDraft} onChange={(event) => setDurationDraft(event.target.value)} required />
                      <span className="bookie-help">Example: 60 minutes = 1 hour.</span>
                    </label>
                    <label className="bookie-label">
                      Price or starting price (NGN)
                      <input name="price" type="number" min={0} step={1} value={priceDraft} onChange={(event) => setPriceDraft(event.target.value)} required />
                    </label>
                    <label className="bookie-label">
                      Different deposit (NGN)
                      <input name="deposit_amount" type="number" min={0} step={1} placeholder="Only if needed" value={depositDraft} onChange={(event) => setDepositDraft(event.target.value)} />
                    </label>
                  </div>

                  <section className="grid gap-3">
                    <h2 className="section-title">How is this priced?</h2>
                    <div className="grid gap-2 md:grid-cols-3">
                      {priceChoices.map((choice) => (
                        <label key={choice.value} className="segmented-option border border-slate-100 bg-white p-4" data-active={pricingMode === choice.value}>
                          <input className="sr-only" type="radio" name="pricing_mode" value={choice.value} checked={pricingMode === choice.value} onChange={() => setPricingMode(choice.value)} />
                          <span className="block text-sm">{choice.label}</span>
                          <span className="mt-1 block text-xs font-medium opacity-75">{choice.hint}</span>
                        </label>
                      ))}
                    </div>
                  </section>

                  <section className="grid gap-3">
                    <h2 className="section-title">What should clients pay now?</h2>
                    <div className="grid gap-2 md:grid-cols-3">
                      {payNowChoices.map((choice) => (
                        <label key={choice.value} className="segmented-option border border-slate-100 bg-white p-4" data-active={depositPolicy === choice.value}>
                          <input className="sr-only" type="radio" name="deposit_policy" value={choice.value} checked={depositPolicy === choice.value} onChange={() => setDepositPolicy(choice.value)} />
                          <span className="block text-sm">{choice.label}</span>
                          <span className="mt-1 block text-xs font-medium opacity-75">{choice.hint}</span>
                        </label>
                      ))}
                    </div>
                  </section>

                  <label className="bookie-label">
                    What clients should know
                    <textarea name="description" placeholder="What is included, what to bring, or when final price is confirmed." value={descriptionDraft} onChange={(event) => setDescriptionDraft(event.target.value)} />
                  </label>

                  {message && <p className="rounded-xl border border-[#0e4731]/15 bg-[#e8efe9] px-4 py-3 text-sm font-semibold text-[#0e4731]">{message}</p>}
                  {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
                </div>

                <aside className="service-preview-panel">
                  <p className="section-title">Client preview</p>
                  <div className="mt-4 rounded-2xl border border-[#0e4731]/10 bg-white p-5 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-xl font-semibold tracking-normal text-[#0f2119]">{nameDraft || "Service name"}</h2>
                        <p className="mt-1 text-sm font-medium text-[#6b7f74]">{Number(durationDraft || 0)} min</p>
                      </div>
                      <span className="rounded-full border border-[#0e4731]/10 bg-[#e8efe9] px-3 py-1 text-xs font-bold text-[#0e4731]">{isActive ? "Bookable" : "Hidden"}</span>
                    </div>
                    <p className="mt-5 text-sm leading-6 text-[#556e61]">{descriptionDraft || "A short note about what this service includes will show here."}</p>
                    <div className="mt-5 grid gap-3 rounded-xl bg-[#f7faf8] p-4 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-[#6b7f74]">Price</span>
                        <strong className="text-right text-[#0f2119]">{previewPriceText}</strong>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-[#6b7f74]">Pay now</span>
                        <strong className="text-right text-[#0e4731]">{previewPayNowText}</strong>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>

              <div className="modal-footer">
                <button type="button" className="secondary-button" onClick={closeEditModal}>Cancel</button>
                <button type="submit">{editingService ? "Save service" : "Add service"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirmOpen && deletingService && (
        <div className="modal-overlay" onClick={closeDeleteConfirm}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h1 className="text-2xl font-semibold tracking-normal text-[#0f2119]">Delete service?</h1>
                <p className="bookie-subtitle mt-1">This removes it from the booking menu.</p>
              </div>
              <button type="button" onClick={closeDeleteConfirm} className="icon-button" aria-label="Close">
                <CloseIcon />
              </button>
            </div>
            <div className="modal-body">
              <p className="text-sm text-[#556e61]">
                Delete <strong>{deletingService.name}</strong>? Clients will not be able to choose it.
              </p>
              {error && <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
            </div>
            <div className="modal-footer">
              <button type="button" className="secondary-button" onClick={closeDeleteConfirm}>Cancel</button>
              <button type="button" className="danger-button" onClick={handleDelete}>Delete service</button>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}
