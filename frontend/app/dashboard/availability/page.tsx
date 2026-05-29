"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, AvailabilityOverride, AvailabilitySchedule, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

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

  async function addOverride(event: FormEvent<HTMLFormElement>) {
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
      <form onSubmit={addSchedule} className="grid gap-3 border border-line bg-white p-4 sm:grid-cols-5">
        <select name="staff_id">
          <option value="">All staff</option>
          {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
        </select>
        <select name="day_of_week" required>
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, index) => <option key={day} value={index}>{day}</option>)}
        </select>
        <input name="start_time" type="time" required />
        <input name="end_time" type="time" required />
        <button type="submit">Add Schedule</button>
      </form>
      <form onSubmit={addOverride} className="grid gap-3 border border-line bg-white p-4 sm:grid-cols-6">
        <select name="staff_id">
          <option value="">All staff</option>
          {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
        </select>
        <input name="date" type="date" required />
        <input name="start_time" type="time" />
        <input name="end_time" type="time" />
        <label className="flex items-center gap-2 text-sm"><input className="w-auto" name="is_unavailable" type="checkbox" />Unavailable</label>
        <input name="reason" placeholder="Reason" />
        <button type="submit">Add Override</button>
      </form>
      <section className="grid gap-3 md:grid-cols-2">
        <div className="border border-line bg-white p-4">
          <h2 className="font-semibold">Weekly</h2>
          {schedules.map((item) => <p key={item.id} className="mt-2 text-sm">{item.day_of_week}: {item.start_time} - {item.end_time}</p>)}
        </div>
        <div className="border border-line bg-white p-4">
          <h2 className="font-semibold">Overrides</h2>
          {overrides.map((item) => <p key={item.id} className="mt-2 text-sm">{item.date}: {item.is_unavailable ? "Unavailable" : `${item.start_time} - ${item.end_time}`}</p>)}
        </div>
      </section>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
