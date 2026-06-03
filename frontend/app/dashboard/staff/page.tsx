"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, Service, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

function initials(name: string) {
  return name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

export default function StaffPage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [serviceDrafts, setServiceDrafts] = useState<Record<string, string[]>>({});
  const [savedDrafts, setSavedDrafts] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load(preferredStaffId?: string) {
    try {
      const [staffRows, serviceRows] = await Promise.all([api.dashboardStaff(), api.dashboardServices()]);
      const drafts = Object.fromEntries(staffRows.map((member) => [member.id, member.service_ids ?? []]));
      setStaff(staffRows);
      setServices(serviceRows);
      setServiceDrafts(drafts);
      setSavedDrafts(drafts);
      setSelectedStaffId(
        preferredStaffId && staffRows.some((member) => member.id === preferredStaffId)
          ? preferredStaffId
          : staffRows[0]?.id ?? "",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load staff");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const selectedStaff = staff.find((member) => member.id === selectedStaffId) ?? staff[0];
  const selectedServices = selectedStaff ? serviceDrafts[selectedStaff.id] ?? [] : [];
  const savedServices = selectedStaff ? savedDrafts[selectedStaff.id] ?? [] : [];
  const isDirty = useMemo(() => {
    const current = [...selectedServices].sort().join(",");
    const saved = [...savedServices].sort().join(",");
    return current !== saved;
  }, [selectedServices, savedServices]);
  const assignedServices = services.filter((service) => selectedServices.includes(service.id));
  const availableServices = services.filter((service) => !selectedServices.includes(service.id));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    const created = await api.createStaff({
      name: form.get("name"),
      bio: form.get("bio") || null,
      avatar_url: null,
      is_bookable: true,
    });
    event.currentTarget.reset();
    setMessage("Staff added");
    await load(created.id);
  }

  async function toggleBookable(member: Staff) {
    setError("");
    setMessage("");
    await api.updateStaff(member.id, { is_bookable: !member.is_bookable });
    setMessage(member.is_bookable ? "Booking turned off" : "Booking turned on");
    await load(member.id);
  }

  function addService(staffId: string, serviceId: string) {
    setServiceDrafts((current) => ({
      ...current,
      [staffId]: Array.from(new Set([...(current[staffId] ?? []), serviceId])),
    }));
  }

  function removeService(staffId: string, serviceId: string) {
    setServiceDrafts((current) => ({
      ...current,
      [staffId]: (current[staffId] ?? []).filter((id) => id !== serviceId),
    }));
  }

  async function saveServices(staffId: string) {
    setError("");
    setMessage("");
    await api.assignStaffServices(staffId, serviceDrafts[staffId] ?? []);
    setMessage("Services saved");
    await load(staffId);
  }

  async function deactivateStaff(staffId: string) {
    setError("");
    setMessage("");
    await api.deleteStaff(staffId);
    setMessage("Staff removed from booking choices");
    await load();
  }

  return (
    <DashboardShell title="Staff">
      <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="grid gap-6">
          <form onSubmit={submit} className="bookie-card grid gap-3 p-5">
            <div>
              <h2 className="section-title">Add staff</h2>
              <p className="bookie-subtitle mt-1">Add someone clients can book with.</p>
            </div>
            <label className="bookie-label">
              Name
              <input name="name" placeholder="Nora James" required />
            </label>
            <label className="bookie-label">
              What they do
              <textarea name="bio" placeholder="Lashes, brows, facials..." rows={3} />
            </label>
            <button type="submit">Add staff</button>
          </form>

          <section className="bookie-card p-5">
            <h2 className="section-title">Team</h2>
            <div className="mt-4 grid gap-2">
              {staff.map((member) => {
                const isSelected = selectedStaff?.id === member.id;
                const count = serviceDrafts[member.id]?.length ?? 0;
                return (
                  <button
                    key={member.id}
                    type="button"
                    onClick={() => setSelectedStaffId(member.id)}
                    className={[
                      "grid min-h-0 grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border p-3 text-left shadow-none hover:translate-y-0",
                      isSelected ? "border-[#0e4731]/20 bg-[#e8efe9]" : "border-slate-100 bg-white hover:bg-[#f8faf9]",
                    ].join(" ")}
                  >
                    <span className={isSelected ? "grid h-11 w-11 place-items-center rounded-full bg-[#0e4731] text-sm font-bold text-white" : "grid h-11 w-11 place-items-center rounded-full bg-[#e8efe9] text-sm font-bold text-[#0e4731]"}>
                      {initials(member.name)}
                    </span>
                    <span className="min-w-0">
                      <strong className="block truncate text-sm text-[#0f2119]">{member.name}</strong>
                      <span className="bookie-help">{count} service{count === 1 ? "" : "s"}</span>
                    </span>
                    <span className="status-badge">{member.is_bookable ? "On" : "Off"}</span>
                  </button>
                );
              })}
              {staff.length === 0 && <p className="soft-empty">No staff yet. Add the first person above.</p>}
            </div>
          </section>
        </aside>

        <section className="bookie-card p-5">
          {selectedStaff ? (
            <div className="grid gap-6">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
                <div className="flex items-start gap-4">
                  <span className="grid h-16 w-16 place-items-center rounded-full bg-[#e8efe9] text-lg font-bold text-[#0e4731]">{initials(selectedStaff.name)}</span>
                  <div>
                    <h1 className="text-2xl font-semibold tracking-normal text-[#0f2119]">{selectedStaff.name}</h1>
                    <p className="bookie-subtitle mt-1 max-w-xl">{selectedStaff.bio || "No notes added yet."}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => toggleBookable(selectedStaff)}
                  className={selectedStaff.is_bookable ? "secondary-button min-h-0 rounded-xl px-4 py-2 text-sm" : "min-h-0 rounded-xl px-4 py-2 text-sm"}
                >
                  {selectedStaff.is_bookable ? "Turn off booking" : "Turn on booking"}
                </button>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <section className="rounded-2xl border border-[#0e4731]/10 bg-[#e8efe9]/60 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="section-title">Assigned to this staff</h2>
                    <span className="status-badge status-badge-success">{assignedServices.length}</span>
                  </div>
                  <div className="mt-4 grid gap-2">
                    {assignedServices.map((service) => (
                      <div key={service.id} className="grid gap-3 rounded-xl border border-white bg-white p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div>
                          <strong className="block text-sm text-[#0f2119]">{service.name}</strong>
                          <span className="bookie-help">{service.duration_minutes} min</span>
                        </div>
                        <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => removeService(selectedStaff.id, service.id)}>
                          Remove
                        </button>
                      </div>
                    ))}
                    {assignedServices.length === 0 && <p className="soft-empty">This staff member has no services yet.</p>}
                  </div>
                </section>

                <section className="rounded-2xl border border-slate-100 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="section-title">Available services</h2>
                    <span className="status-badge">{availableServices.length}</span>
                  </div>
                  <div className="mt-4 grid gap-2">
                    {availableServices.map((service) => (
                      <div key={service.id} className="grid gap-3 rounded-xl border border-slate-100 bg-[#f8faf9] p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div>
                          <strong className="block text-sm text-[#0f2119]">{service.name}</strong>
                          <span className="bookie-help">{service.duration_minutes} min</span>
                        </div>
                        <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => addService(selectedStaff.id, service.id)}>
                          Add
                        </button>
                      </div>
                    ))}
                    {availableServices.length === 0 && <p className="soft-empty">All services are assigned to this staff member.</p>}
                  </div>
                </section>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
                <button type="button" onClick={() => deactivateStaff(selectedStaff.id)} className="danger-link min-h-0 rounded-xl px-4 py-2 text-sm">
                  Remove from bookings
                </button>
                <div className="flex items-center gap-3">
                  {isDirty && <span className="text-sm font-semibold text-[#caa26b]">Unsaved changes</span>}
                  <button type="button" onClick={() => saveServices(selectedStaff.id)} disabled={!isDirty} className="min-h-0 rounded-xl px-5 py-2 text-sm">
                    Save services
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <p className="soft-empty">Add a staff member to choose their services.</p>
          )}
        </section>
      </section>
      {message && <p className="rounded-xl border border-[#0e4731]/15 bg-[#e8efe9] px-4 py-3 text-sm font-semibold text-[#0e4731]">{message}</p>}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
    </DashboardShell>
  );
}
