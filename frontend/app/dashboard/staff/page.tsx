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

  async function assignServices(staffId: string, form: HTMLFormElement) {
    const data = new FormData(form);
    await api.assignStaffServices(staffId, data.getAll("service_ids").map(String));
  }

  return (
    <DashboardShell title="Staff">
      <form onSubmit={submit} className="grid gap-3 border border-line bg-white p-4 sm:grid-cols-3">
        <input name="name" placeholder="Staff name" required />
        <input name="bio" placeholder="Bio" />
        <button type="submit">Add Staff</button>
      </form>
      <section className="grid gap-3">
        {staff.map((member) => (
          <div key={member.id} className="grid gap-3 border border-line bg-white p-4">
            <div className="flex items-center justify-between">
              <strong>{member.name}</strong>
              <button type="button" onClick={async () => { await api.deleteStaff(member.id); await load(); }}>Deactivate</button>
            </div>
            <form onSubmit={async (event) => { event.preventDefault(); await assignServices(member.id, event.currentTarget); }} className="flex flex-wrap gap-3">
              {services.map((service) => (
                <label key={service.id} className="flex items-center gap-2 text-sm">
                  <input className="w-auto" type="checkbox" name="service_ids" value={service.id} />
                  {service.name}
                </label>
              ))}
              <button type="submit">Assign Services</button>
            </form>
          </div>
        ))}
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
