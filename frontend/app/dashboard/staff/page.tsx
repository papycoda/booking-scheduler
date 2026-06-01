"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, Service, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

export default function StaffPage() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const [staffRows, serviceRows] = await Promise.all([api.dashboardStaff(), api.dashboardServices()]);
      setStaff(staffRows);
      setServices(serviceRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load staff");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createStaff({
      name: form.get("name"),
      bio: form.get("bio") || null,
      avatar_url: null,
      is_bookable: true,
    });
    event.currentTarget.reset();
    await load();
  }

  async function toggleBookable(member: Staff) {
    await api.updateStaff(member.id, { is_bookable: !member.is_bookable });
    await load();
  }

  async function assignServices(staffId: string, form: HTMLFormElement) {
    const data = new FormData(form);
    await api.assignStaffServices(staffId, data.getAll("service_ids").map(String));
  }

  return (
    <DashboardShell title="Staff">
      <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <form onSubmit={submit} className="dashboard-card grid gap-4 p-5 lg:self-start">
          <div>
            <p className="eyebrow">Team</p>
            <h2 className="section-title">Add staff</h2>
          </div>
          <input name="name" placeholder="Staff name" required />
          <textarea name="bio" placeholder="Bio or specialty" />
          <button type="submit">Add staff</button>
        </form>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {staff.map((member) => (
            <article key={member.id} className="dashboard-card grid gap-4 p-5">
              <div className="grid justify-items-center gap-3 text-center">
                <div className="grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-[#dce8df] to-white text-2xl font-black text-action ring-8 ring-action/5">
                  {member.name.slice(0, 1).toUpperCase()}
                </div>
                <div>
                  <h2 className="font-bold text-ink">{member.name}</h2>
                  {member.bio && <p className="mt-1 text-xs font-medium text-ink/60">{member.bio}</p>}
                </div>
                <button
                  className={member.is_bookable ? "status-badge status-badge-success" : "status-badge status-badge-muted"}
                  type="button"
                  onClick={() => toggleBookable(member)}
                >
                  {member.is_bookable ? "Bookable" : "Off-Duty"}
                </button>
              </div>

              <form onSubmit={async (event) => { event.preventDefault(); await assignServices(member.id, event.currentTarget); }} className="grid gap-3 border-t border-line/60 pt-4">
                <p className="text-xs font-bold uppercase tracking-wider text-ink/55">Service assignment</p>
                <div className="flex flex-wrap gap-2">
                  {services.map((service) => (
                    <label key={service.id} className="tag-button has-[:checked]:border-action has-[:checked]:bg-action has-[:checked]:text-white">
                      <input className="sr-only" type="checkbox" name="service_ids" value={service.id} />
                      {service.name}
                    </label>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="submit" className="min-h-0 rounded-xl px-3 py-2 text-xs">Assign</button>
                  <button className="danger-link min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={async () => { await api.deleteStaff(member.id); await load(); }}>
                    Deactivate
                  </button>
                </div>
              </form>
            </article>
          ))}
          {staff.length === 0 && <p className="dashboard-card p-5 text-sm text-ink/65">No staff yet.</p>}
        </section>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
