"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Service, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function shortBio(bio?: string | null) {
  if (!bio) return "Team member";
  return bio.length > 44 ? `${bio.slice(0, 44)}...` : bio;
}

export default function StaffPage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [serviceDrafts, setServiceDrafts] = useState<Record<string, string[]>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load(preferredStaffId?: string) {
    try {
      const [staffRows, serviceRows] = await Promise.all([api.dashboardStaff(), api.dashboardServices()]);
      setStaff(staffRows);
      setServices(serviceRows);
      setServiceDrafts(Object.fromEntries(staffRows.map((member) => [member.id, member.service_ids ?? []])));
      const nextSelected = preferredStaffId && staffRows.some((member) => member.id === preferredStaffId)
        ? preferredStaffId
        : staffRows[0]?.id ?? "";
      setSelectedStaffId(nextSelected);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load staff");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const selectedStaff = staff.find((member) => member.id === selectedStaffId) ?? staff[0];
  const selectedServices = selectedStaff ? serviceDrafts[selectedStaff.id] ?? [] : [];

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
    setMessage(member.is_bookable ? "Bookings turned off" : "Bookings turned on");
    await load(member.id);
  }

  function toggleService(staffId: string, serviceId: string) {
    setServiceDrafts((current) => {
      const selected = current[staffId] ?? [];
      const next = selected.includes(serviceId) ? selected.filter((id) => id !== serviceId) : [...selected, serviceId];
      return { ...current, [staffId]: next };
    });
  }

  async function assignServices(staffId: string) {
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
    setMessage("Staff removed from bookings");
    await load();
  }

  return (
    <DashboardShell title="Staff">
      <section className="dashboard-card overflow-hidden">
        <div className="border-b border-line/70 bg-[#fcfdfe] p-6">
          <p className="eyebrow">Team</p>
          <h2 className="section-title mt-1">Staff and services</h2>
          <p className="muted mt-1">Choose a staff member, then pick the services they can take.</p>
        </div>

        <div className="grid min-h-[640px] divide-y divide-line/70 lg:grid-cols-12 lg:divide-x lg:divide-y-0">
          <aside className="grid gap-6 bg-[#fcfdfe]/60 p-5 lg:col-span-5">
            <form onSubmit={submit} className="grid gap-3 rounded-2xl border border-line/70 bg-white p-4 shadow-sm">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-ink/55">Add staff</p>
              </div>
              <input name="name" placeholder="Staff name" required />
              <textarea name="bio" placeholder="Bio or specialty" rows={3} />
              <button type="submit">Add staff</button>
            </form>

            <div className="grid content-start gap-3">
              <p className="text-xs font-bold uppercase tracking-wider text-ink/55">Team list</p>
              <div className="grid gap-2">
                {staff.map((member) => {
                  const isSelected = member.id === selectedStaff?.id;
                  return (
                    <button
                      key={member.id}
                      type="button"
                      onClick={() => setSelectedStaffId(member.id)}
                      className={[
                        "flex min-h-0 items-center justify-between rounded-xl border p-3 text-left text-ink shadow-none transition hover:translate-y-0",
                        isSelected ? "border-action/20 bg-[#e8efe9]/80" : "border-line/70 bg-white hover:bg-[#f8faf9]",
                      ].join(" ")}
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <span className={["grid h-10 w-10 shrink-0 place-items-center rounded-full text-xs font-bold", isSelected ? "bg-action text-white" : "border border-[#caa26b]/20 bg-[#caa26b]/10 text-[#9a7546]"].join(" ")}>
                          {initials(member.name)}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-bold">{member.name}</span>
                          <span className="block truncate text-xs font-medium text-ink/55">{shortBio(member.bio)}</span>
                        </span>
                      </span>
                      <span className="rounded-md bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-ink/55">
                        {member.is_bookable ? "On" : "Off"}
                      </span>
                    </button>
                  );
                })}
                {staff.length === 0 && <p className="rounded-xl border border-line/70 bg-white p-4 text-sm text-ink/65">No staff yet.</p>}
              </div>
            </div>
          </aside>

          <section className="flex flex-col justify-between bg-white p-6 lg:col-span-7">
            {selectedStaff ? (
              <>
                <div className="grid gap-6">
                  <div className="flex flex-col justify-between gap-4 border-b border-line/70 pb-5 sm:flex-row sm:items-start">
                    <div className="flex items-start gap-4">
                      <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full border border-action/10 bg-[#e8efe9] text-lg font-bold text-action shadow-inner">
                        {initials(selectedStaff.name)}
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-ink">{selectedStaff.name}</h2>
                        {selectedStaff.bio && <p className="mt-1 max-w-md text-sm font-medium leading-relaxed text-ink/60">{selectedStaff.bio}</p>}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleBookable(selectedStaff)}
                      className={selectedStaff.is_bookable ? "status-badge status-badge-success min-h-0 px-4 py-2" : "status-badge status-badge-muted min-h-0 px-4 py-2"}
                    >
                      {selectedStaff.is_bookable ? "Taking bookings" : "Not taking bookings"}
                    </button>
                  </div>

                  <div>
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-ink/55">Services</h3>
                      <span className="text-xs font-semibold text-ink/55">{selectedServices.length} selected</span>
                    </div>
                    <div className="grid gap-2.5 sm:grid-cols-2">
                      {services.map((service) => {
                        const isAssigned = selectedServices.includes(service.id);
                        return (
                          <label
                            key={service.id}
                            className={[
                              "flex cursor-pointer items-center justify-between rounded-xl border p-3 transition",
                              isAssigned ? "border-action/20 bg-[#e8efe9]/70" : "border-line/70 bg-white hover:bg-[#f8faf9]",
                            ].join(" ")}
                          >
                            <span className={isAssigned ? "text-xs font-bold text-ink" : "text-xs font-semibold text-ink/60"}>{service.name}</span>
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-[#0e4731]"
                              checked={isAssigned}
                              onChange={() => toggleService(selectedStaff.id, service.id)}
                            />
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-line/70 pt-5">
                  <button type="button" onClick={() => deactivateStaff(selectedStaff.id)} className="danger-link min-h-0 rounded-xl px-4 py-2 text-xs">
                    Remove from bookings
                  </button>
                  <button type="button" onClick={() => assignServices(selectedStaff.id)} className="min-h-0 rounded-xl px-6 py-2 text-xs">
                    Save services
                  </button>
                </div>
              </>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <p className="muted">Add a staff member to assign services.</p>
              </div>
            )}
          </section>
        </div>
      </section>
      {message && <p className="text-sm text-action">{message}</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
