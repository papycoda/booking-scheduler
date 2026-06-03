"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, AvailabilityOverride, AvailabilitySchedule, DashboardBooking, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const hours = Array.from({ length: 11 }, (_, index) => index + 8);
const timelineStart = 8 * 60;
const timelineEnd = 19 * 60;
const timelineMinutes = timelineEnd - timelineStart;

function dateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function dateFromInput(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function timeMinutes(value?: string | null) {
  if (!value) return timelineStart;
  const [hoursPart, minutesPart] = value.split(":").map(Number);
  return hoursPart * 60 + (minutesPart || 0);
}

function blockStyle(start?: string | null, end?: string | null) {
  const startMinute = Math.max(timeMinutes(start), timelineStart);
  const endMinute = Math.min(timeMinutes(end), timelineEnd);
  const top = ((startMinute - timelineStart) / timelineMinutes) * 100;
  const height = Math.max(((endMinute - startMinute) / timelineMinutes) * 100, 6);
  return { top: `${top}%`, height: `${height}%` };
}

function bookingStyle(start: string, end: string) {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return blockStyle(
    `${String(startDate.getHours()).padStart(2, "0")}:${String(startDate.getMinutes()).padStart(2, "0")}`,
    `${String(endDate.getHours()).padStart(2, "0")}:${String(endDate.getMinutes()).padStart(2, "0")}`,
  );
}

export default function AvailabilityPage() {
  const [schedules, setSchedules] = useState<AvailabilitySchedule[]>([]);
  const [timeOff, setTimeOff] = useState<AvailabilityOverride[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [bookings, setBookings] = useState<DashboardBooking[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [viewMode, setViewMode] = useState<"staff" | "week">("staff");
  const [selectedDate, setSelectedDate] = useState(dateInputValue(new Date()));
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const start = dateInputValue(addDays(new Date(selectedDate), -7));
      const end = dateInputValue(addDays(new Date(selectedDate), 14));
      const [scheduleRows, timeOffRows, staffRows, bookingRows] = await Promise.all([
        api.schedules(),
        api.overrides(start, end),
        api.dashboardStaff(),
        api.dashboardBookings(),
      ]);
      setSchedules(scheduleRows);
      setTimeOff(timeOffRows);
      setStaff(staffRows);
      setBookings(bookingRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load hours");
    }
  }

  useEffect(() => {
    load();
  }, [selectedDate]);

  const staffNameById = useMemo(() => new Map(staff.map((member) => [member.id, member.name])), [staff]);
  const selectedStaff = staff.find((member) => member.id === selectedStaffId);
  const weekStart = useMemo(() => {
    const date = new Date(selectedDate);
    const day = (date.getDay() + 6) % 7;
    return addDays(date, -day);
  }, [selectedDate]);

  const columns = viewMode === "staff"
    ? selectedStaff ? [selectedStaff] : staff
    : weekdays.map((label, index) => ({ id: String(index), name: label, is_bookable: true, is_active: true }));

  function schedulesForColumn(columnId: string) {
    if (viewMode === "staff") {
      const date = new Date(selectedDate);
      const weekday = (date.getDay() + 6) % 7;
      return schedules.filter((row) => row.is_active && row.day_of_week === weekday && (!row.staff_id || row.staff_id === columnId));
    }
    return schedules.filter((row) => row.is_active && row.day_of_week === Number(columnId) && (!selectedStaffId || !row.staff_id || row.staff_id === selectedStaffId));
  }

  function timeOffForColumn(columnId: string) {
    if (viewMode === "staff") {
      return timeOff.filter((row) => row.date === selectedDate && (!row.staff_id || row.staff_id === columnId));
    }
    const date = dateInputValue(addDays(weekStart, Number(columnId)));
    return timeOff.filter((row) => row.date === date && (!selectedStaffId || !row.staff_id || row.staff_id === selectedStaffId));
  }

  function bookingsForColumn(columnId: string) {
    return bookings.filter((booking) => {
      if (["cancelled", "expired"].includes(booking.status)) return false;
      const date = viewMode === "staff" ? selectedDate : dateInputValue(addDays(weekStart, Number(columnId)));
      if (dateInputValue(new Date(booking.start_time)) !== date) return false;
      if (viewMode === "staff") return booking.staff_name === staffNameById.get(columnId);
      return !selectedStaffId || booking.staff_name === selectedStaff?.name;
    });
  }

  function moveDate(direction: -1 | 1) {
    const days = viewMode === "week" ? 7 : 1;
    setSelectedDate(dateInputValue(addDays(dateFromInput(selectedDate), direction * days)));
  }

  async function addWorkingHours(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    await api.createSchedule({
      staff_id: form.get("staff_id") || null,
      day_of_week: Number(form.get("day_of_week")),
      start_time: form.get("start_time"),
      end_time: form.get("end_time"),
      is_active: true,
    });
    setMessage("Working hours saved");
    event.currentTarget.reset();
    await load();
  }

  async function addTimeOff(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    await api.createOverride({
      staff_id: form.get("staff_id") || null,
      date: form.get("date"),
      start_time: form.get("start_time") || null,
      end_time: form.get("end_time") || null,
      is_unavailable: true,
      reason: form.get("reason") || null,
    });
    setMessage("Time off saved");
    event.currentTarget.reset();
    await load();
  }

  async function removeSchedule(id: string) {
    await api.deleteSchedule(id);
    setMessage("Hours removed");
    await load();
  }

  async function removeTimeOff(id: string) {
    await api.deleteOverride(id);
    setMessage("Time off removed");
    await load();
  }

  return (
    <DashboardShell title="Availability">
      <section className="grid gap-6">
        <div className="bookie-card p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-[#0f2119]">Hours and time off</h1>
              <p className="bookie-subtitle mt-1">See who is working and block time when needed.</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="bookie-label min-w-[180px]">
                View
                <select value={viewMode} onChange={(event) => setViewMode(event.target.value as "staff" | "week")}>
                  <option value="staff">Day</option>
                  <option value="week">Week</option>
                </select>
              </label>
              <label className="bookie-label min-w-[180px]">
                Staff
                <select value={selectedStaffId} onChange={(event) => setSelectedStaffId(event.target.value)}>
                  <option value="">All staff</option>
                  {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                </select>
              </label>
              <label className="bookie-label min-w-[170px]">
                Date
                <span className="date-stepper">
                  <button type="button" className="date-stepper-button" onClick={() => moveDate(-1)} aria-label={viewMode === "week" ? "Previous week" : "Previous day"}>
                    &lt;
                  </button>
                  <input type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
                  <button type="button" className="date-stepper-button" onClick={() => moveDate(1)} aria-label={viewMode === "week" ? "Next week" : "Next day"}>
                    &gt;
                  </button>
                </span>
              </label>
            </div>
          </div>
        </div>

        <section className="timeline-grid">
          <div className="grid min-w-max" style={{ gridTemplateColumns: `72px repeat(${Math.max(columns.length, 1)}, minmax(180px, 1fr))` }}>
            <div className="border-b border-slate-100 bg-white p-3" />
            {columns.map((column) => (
              <div key={column.id} className="border-b border-l border-slate-100 bg-white p-3">
                <strong className="block text-sm text-[#0f2119]">{column.name}</strong>
                <span className="bookie-help">
                  {viewMode === "week" ? dateInputValue(addDays(weekStart, Number(column.id))) : "Working day"}
                </span>
              </div>
            ))}
          </div>
          <div className="grid min-h-[620px] min-w-max" style={{ gridTemplateColumns: `72px repeat(${Math.max(columns.length, 1)}, minmax(180px, 1fr))` }}>
            <div className="relative border-r border-slate-100 bg-[#f8faf9]">
              {hours.map((hour) => (
                <span key={hour} className="timeline-time absolute left-3" style={{ top: `${((hour * 60 - timelineStart) / timelineMinutes) * 100}%` }}>
                  {String(hour).padStart(2, "0")}:00
                </span>
              ))}
            </div>
            {columns.map((column) => (
              <div key={column.id} className="relative border-l border-slate-100 bg-white">
                {hours.map((hour) => (
                  <div key={hour} className="absolute left-0 right-0 border-t border-slate-100" style={{ top: `${((hour * 60 - timelineStart) / timelineMinutes) * 100}%` }} />
                ))}
                {schedulesForColumn(column.id).map((row) => (
                  <div key={row.id} className="timeline-block timeline-work left-3 right-3" style={blockStyle(row.start_time, row.end_time)}>
                    Working {row.start_time.slice(0, 5)}-{row.end_time.slice(0, 5)}
                  </div>
                ))}
                {timeOffForColumn(column.id).map((row) => (
                  <div key={row.id} className="timeline-block timeline-timeoff left-5 right-5" style={blockStyle(row.start_time || "08:00", row.end_time || "19:00")}>
                    Time off{row.reason ? `: ${row.reason}` : ""}
                  </div>
                ))}
                {bookingsForColumn(column.id).map((booking) => (
                  <div key={booking.id} className="timeline-block timeline-booking left-7 right-7" style={bookingStyle(booking.start_time, booking.end_time)}>
                    {booking.client_name}
                    <span className="block font-medium opacity-80">{booking.service_name}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <form onSubmit={addWorkingHours} className="bookie-card grid gap-4 p-5">
            <div>
              <h2 className="section-title">Set working hours</h2>
              <p className="bookie-subtitle mt-1">Choose who is working, the day, and the time.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="bookie-label">Staff<select name="staff_id"><option value="">All staff</option>{staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}</select></label>
              <label className="bookie-label">Day<select name="day_of_week">{weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}</select></label>
              <label className="bookie-label">Start<input name="start_time" type="time" defaultValue="09:00" required /></label>
              <label className="bookie-label">End<input name="end_time" type="time" defaultValue="18:00" required /></label>
            </div>
            <button type="submit">Save hours</button>
          </form>

          <form onSubmit={addTimeOff} className="bookie-card grid gap-4 p-5">
            <div>
              <h2 className="section-title">Add time off</h2>
              <p className="bookie-subtitle mt-1">Block a day or a few hours from booking.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="bookie-label">Staff<select name="staff_id"><option value="">All staff</option>{staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}</select></label>
              <label className="bookie-label">Date<input name="date" type="date" defaultValue={selectedDate} required /></label>
              <label className="bookie-label">Start<input name="start_time" type="time" /></label>
              <label className="bookie-label">End<input name="end_time" type="time" /></label>
              <label className="bookie-label sm:col-span-2">Note<input name="reason" placeholder="Holiday, break, personal time..." /></label>
            </div>
            <button type="submit">Add time off</button>
          </form>
        </section>

        <section className="hidden">
          <div className="bookie-card p-5">
            <h2 className="section-title">Saved working hours</h2>
            <div className="mt-4 grid gap-2">
              {schedules.slice(0, 12).map((row) => (
                <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-100 bg-[#f8faf9] p-3">
                  <span className="text-sm font-semibold text-[#0f2119]">{row.staff_id ? staffNameById.get(row.staff_id) : "All staff"} · {weekdays[row.day_of_week]} · {row.start_time.slice(0, 5)}-{row.end_time.slice(0, 5)}</span>
                  <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => removeSchedule(row.id)}>Remove</button>
                </div>
              ))}
              {schedules.length === 0 && <p className="soft-empty">No hours set yet.</p>}
            </div>
          </div>

          <div className="bookie-card p-5">
            <h2 className="section-title">Saved time off</h2>
            <div className="mt-4 grid gap-2">
              {timeOff.slice(0, 12).map((row) => (
                <div key={row.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#caa26b]/30 bg-[#fffaf2] p-3">
                  <span className="text-sm font-semibold text-[#0f2119]">{row.staff_id ? staffNameById.get(row.staff_id) : "All staff"} · {row.date}{row.start_time ? ` · ${row.start_time.slice(0, 5)}-${row.end_time?.slice(0, 5)}` : ""}</span>
                  <button className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs" type="button" onClick={() => removeTimeOff(row.id)}>Remove</button>
                </div>
              ))}
              {timeOff.length === 0 && <p className="soft-empty">No time off saved.</p>}
            </div>
          </div>
        </section>
      </section>
      {message && <p className="rounded-xl border border-[#0e4731]/15 bg-[#e8efe9] px-4 py-3 text-sm font-semibold text-[#0e4731]">{message}</p>}
      {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</p>}
    </DashboardShell>
  );
}
