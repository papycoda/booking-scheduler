"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, AvailabilityOverride, AvailabilitySchedule, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function AvailabilityPage() {
  const [schedules, setSchedules] = useState<AvailabilitySchedule[]>([]);
  const [overrides, setOverrides] = useState<AvailabilityOverride[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const today = new Date().toISOString().slice(0, 10);
      const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
      const [scheduleRows, overrideRows, staffRows] = await Promise.all([api.schedules(), api.overrides(today, future), api.dashboardStaff()]);
      setSchedules(scheduleRows);
      setOverrides(overrideRows);
      setStaff(staffRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load availability");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function addSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.createSchedule({
      staff_id: form.get("staff_id") || null,
      day_of_week: Number(form.get("day_of_week")),
      start_time: form.get("start_time"),
      end_time: form.get("end_time"),
      is_active: true,
    });
    event.currentTarget.reset();
    await load();
  }

  async function addException(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const isUnavailable = form.get("is_unavailable") === "on";
    await api.createOverride({
      staff_id: form.get("staff_id") || null,
      date: form.get("date"),
      is_unavailable: isUnavailable,
      start_time: isUnavailable ? null : form.get("start_time"),
      end_time: isUnavailable ? null : form.get("end_time"),
      reason: form.get("reason") || null,
    });
    event.currentTarget.reset();
    await load();
  }

  return (
    <DashboardShell title="Availability">
      <section className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="grid gap-6">
          <form onSubmit={addSchedule} className="dashboard-card grid gap-5 p-5">
            <div>
              <p className="eyebrow">Weekly hours</p>
              <h2 className="section-title">Add a regular schedule</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <select name="staff_id">
                <option value="">All staff</option>
                {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
              </select>
              <select name="day_of_week" required>
                {days.map((day, index) => <option key={day} value={index}>{day}</option>)}
              </select>
              <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                Start
                <input name="start_time" type="time" required />
              </label>
              <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                End
                <input name="end_time" type="time" required />
              </label>
              <button type="submit">Add schedule</button>
            </div>
          </form>

          <section className="dashboard-card p-5">
            <div className="mb-4">
              <p className="eyebrow">Weekly</p>
              <h2 className="section-title">Schedule blocks</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {schedules.map((item) => (
                <article key={item.id} className="rounded-2xl border border-line/70 bg-[#fcfdfe] p-4">
                  <div className="flex items-center justify-between">
                    <strong>{days[item.day_of_week] ?? item.day_of_week}</strong>
                    <span className="status-badge status-badge-success">Active</span>
                  </div>
                  <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-center">
                    <span className="rounded-xl bg-white px-3 py-2 text-sm font-bold">{item.start_time}</span>
                    <span className="text-xs font-bold text-ink/40">to</span>
                    <span className="rounded-xl bg-white px-3 py-2 text-sm font-bold">{item.end_time}</span>
                  </div>
                </article>
              ))}
              {schedules.length === 0 && <p className="muted">No weekly hours yet.</p>}
            </div>
          </section>
        </div>

        <aside className="grid gap-6">
          <form onSubmit={addException} className="dashboard-card grid gap-4 p-5">
            <div>
              <p className="eyebrow">Exceptions</p>
              <h2 className="section-title">Add an exception</h2>
            </div>
            <select name="staff_id">
              <option value="">All staff</option>
              {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
            </select>
            <input name="date" type="date" required />
            <div className="grid grid-cols-2 gap-3">
              <input name="start_time" type="time" />
              <input name="end_time" type="time" />
            </div>
            <label className="flex items-center justify-between rounded-xl border border-line/70 bg-[#fcfdfe] px-3 py-2 text-sm font-semibold">
              Unavailable
              <input className="h-4 w-4 accent-[#0e4731]" name="is_unavailable" type="checkbox" />
            </label>
            <input name="reason" placeholder="Reason" />
            <button type="submit">Add exception</button>
          </form>

          <section className="dashboard-card p-5">
            <div className="mb-4">
              <p className="eyebrow">Exceptions</p>
              <h2 className="section-title">Modified dates</h2>
            </div>
            <div className="grid gap-3">
              {overrides.map((item) => (
                <article key={item.id} className="rounded-2xl border border-[#caa26b]/60 bg-[#fffaf2] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <strong>{new Date(`${item.date}T00:00:00`).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}</strong>
                    <span className="status-badge">{item.is_unavailable ? "Unavailable" : "Modified"}</span>
                  </div>
                  <p className="mt-2 text-sm text-ink/65">{item.is_unavailable ? "No bookings accepted." : `${item.start_time} - ${item.end_time}`}</p>
                  {item.reason && <p className="mt-1 text-xs font-medium text-ink/55">{item.reason}</p>}
                </article>
              ))}
              {overrides.length === 0 && <p className="muted">No exceptions in the next 30 days.</p>}
            </div>
          </section>
        </aside>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
