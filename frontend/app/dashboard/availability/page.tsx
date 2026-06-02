"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, AvailabilityOverride, AvailabilitySchedule, DashboardBooking, Staff } from "../../../lib/api";
import { DashboardShell } from "../../../components/DashboardShell";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const timelineStartHour = 9;
const timelineEndHour = 18;
const timelineMinutes = (timelineEndHour - timelineStartHour) * 60;

function dateInputValue(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function addDays(date: Date, daysToAdd: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + daysToAdd);
  return next;
}

function startOfWeek(date: Date) {
  const next = new Date(date);
  const day = (next.getDay() + 6) % 7;
  next.setDate(next.getDate() - day);
  return next;
}

function dateLabel(date: Date, long = false) {
  return date.toLocaleDateString([], long ? { weekday: "long", month: "long", day: "numeric" } : { month: "short", day: "numeric" });
}

function formatTime(value?: string | null) {
  if (!value) return "--:--";
  return value.slice(0, 5);
}

function timeToMinutes(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

function dateTimeToLocalMinutes(value: string) {
  const date = new Date(value);
  return date.getHours() * 60 + date.getMinutes();
}

function blockStyle(startMinutes: number, endMinutes: number) {
  const start = Math.max(0, startMinutes - timelineStartHour * 60);
  const end = Math.min(timelineMinutes, endMinutes - timelineStartHour * 60);
  return {
    top: `${(start / timelineMinutes) * 100}%`,
    height: `${Math.max(6, ((end - start) / timelineMinutes) * 100)}%`,
  };
}

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function AvailabilityPage() {
  const [schedules, setSchedules] = useState<AvailabilitySchedule[]>([]);
  const [overrides, setOverrides] = useState<AvailabilityOverride[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [bookings, setBookings] = useState<DashboardBooking[]>([]);
  const [selectedDate, setSelectedDate] = useState(dateInputValue(new Date()));
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [viewMode, setViewMode] = useState<"timeline" | "week">("timeline");
  const [activeEditor, setActiveEditor] = useState<"schedule" | "exception" | null>(null);
  const [exceptionUnavailable, setExceptionUnavailable] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      const baseDate = new Date(`${selectedDate}T00:00:00`);
      const from = dateInputValue(startOfWeek(baseDate));
      const to = dateInputValue(addDays(startOfWeek(baseDate), 6));
      const [scheduleRows, overrideRows, staffRows, bookingRows] = await Promise.all([
        api.schedules(),
        api.overrides(from, to),
        api.dashboardStaff(),
        api.dashboardBookings(),
      ]);
      setSchedules(scheduleRows);
      setOverrides(overrideRows);
      setStaff(staffRows);
      setBookings(bookingRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load availability");
    }
  }

  useEffect(() => {
    load();
  }, [selectedDate]);

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
    setActiveEditor(null);
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
    setExceptionUnavailable(true);
    setActiveEditor(null);
    await load();
  }

  async function removeSchedule(scheduleId: string) {
    await api.deleteSchedule(scheduleId);
    await load();
  }

  async function removeException(overrideId: string) {
    await api.deleteOverride(overrideId);
    await load();
  }

  const selectedDay = new Date(`${selectedDate}T00:00:00`);
  const weekStart = startOfWeek(selectedDay);
  const weekDays = Array.from({ length: 5 }, (_, index) => addDays(weekStart, index));
  const visibleStaff = selectedStaffId ? staff.filter((member) => member.id === selectedStaffId) : staff;
  const staffNameById = new Map(staff.map((member) => [member.id, member.name]));
  const selectedStaffName = selectedStaffId ? staffNameById.get(selectedStaffId) || "Staff member" : "All staff";

  const activeBookings = bookings.filter((booking) => !["cancelled", "expired"].includes(booking.status));
  const activeSchedules = schedules.filter((item) => item.is_active).length;
  const upcomingExceptions = overrides.filter((item) => item.date >= selectedDate);

  function schedulesFor(staffId: string, date: Date) {
    const weekday = (date.getDay() + 6) % 7;
    return schedules.filter((item) => item.is_active && item.day_of_week === weekday && (!item.staff_id || item.staff_id === staffId));
  }

  function exceptionsFor(staffId: string, date: Date) {
    const key = dateInputValue(date);
    return overrides.filter((item) => item.date === key && (!item.staff_id || item.staff_id === staffId));
  }

  function bookingsFor(staffId: string, date: Date) {
    const key = dateInputValue(date);
    return activeBookings.filter((booking) => booking.staff_name === staffNameById.get(staffId) && dateInputValue(new Date(booking.start_time)) === key);
  }

  const dailyColumns = visibleStaff.length ? visibleStaff : staff.slice(0, 1);

  return (
    <DashboardShell title="Availability">
      <section className="dashboard-card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-line/70 bg-[#fcfdfe] p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="eyebrow">Availability management</p>
            <h2 className="section-title mt-1">Staff timeline workspace</h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="segmented-control">
              <button type="button" className="segmented-option min-h-0 border-0 bg-transparent px-4 py-2 shadow-none" data-active={viewMode === "timeline"} onClick={() => setViewMode("timeline")}>
                Timeline
              </button>
              <button type="button" className="segmented-option min-h-0 border-0 bg-transparent px-4 py-2 shadow-none" data-active={viewMode === "week"} onClick={() => setViewMode("week")}>
                Weekly grid
              </button>
            </div>
            <button type="button" className="secondary-button min-h-0 rounded-xl px-4 py-2 text-xs" onClick={() => setActiveEditor("schedule")}>
              Set hours
            </button>
            <button type="button" className="min-h-0 rounded-xl px-4 py-2 text-xs" onClick={() => setActiveEditor("exception")}>
              Add exception
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-4 border-b border-line/70 bg-white p-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <button type="button" className="secondary-button min-h-0 rounded-lg px-2 py-1" onClick={() => setSelectedDate(dateInputValue(addDays(selectedDay, viewMode === "week" ? -7 : -1)))}>
                &lt;
              </button>
              <input className="w-auto min-w-[11rem] rounded-lg px-3 py-1.5 text-sm font-bold" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
              <button type="button" className="secondary-button min-h-0 rounded-lg px-2 py-1" onClick={() => setSelectedDate(dateInputValue(addDays(selectedDay, viewMode === "week" ? 7 : 1)))}>
                &gt;
              </button>
            </div>
            <div className="h-5 w-px bg-line hidden sm:block" />
            <label className="flex items-center gap-2 text-xs font-bold text-ink/60">
              Staff
              <select className="min-h-0 w-48 rounded-lg px-3 py-1.5 text-xs font-semibold" value={selectedStaffId} onChange={(event) => setSelectedStaffId(event.target.value)}>
                <option value="">All staff</option>
                {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
              </select>
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs font-semibold text-ink/60">
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded border border-action/10 bg-[#e8efe9]" /> Available window</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-action" /> Booked slot</span>
            <span className="inline-flex items-center gap-1.5"><span className="availability-stripes h-3 w-3 rounded border border-line" /> Exception</span>
          </div>
        </div>

        <div className="overflow-x-auto bg-white">
          {viewMode === "timeline" ? (
            <div className="min-w-[760px]">
              <div className="flex border-b border-line/60 bg-[#f4f6f5]/50 py-4">
                <div className="w-24 shrink-0 text-center text-[11px] font-bold uppercase tracking-wider text-ink/55">Time</div>
                <div className="grid flex-1 text-center" style={{ gridTemplateColumns: `repeat(${Math.max(1, dailyColumns.length)}, minmax(220px, 1fr))` }}>
                  {dailyColumns.map((member) => (
                    <div key={member.id} className="flex items-center justify-center gap-3 border-r border-line/50 last:border-r-0">
                      <span className="grid h-8 w-8 place-items-center rounded-full bg-action/10 text-[10px] font-bold text-action">{initials(member.name)}</span>
                      <span className="text-left">
                        <span className="block text-xs font-bold text-ink">{member.name}</span>
                        <span className="block text-[10px] font-medium text-ink/55">{dateLabel(selectedDay, true)}</span>
                      </span>
                    </div>
                  ))}
                  {dailyColumns.length === 0 && <p className="text-sm font-semibold text-ink/60">Add staff to build the timeline.</p>}
                </div>
              </div>
              <div className="relative flex h-[630px]">
                <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                  {Array.from({ length: 10 }).map((_, index) => <div key={index} className="h-0 w-full border-b border-line/60" />)}
                </div>
                <div className="z-10 flex w-24 shrink-0 flex-col justify-between border-r border-line/70 bg-[#fcfdfe] py-2 text-center text-[11px] font-bold text-ink/55">
                  {Array.from({ length: 10 }).map((_, index) => <div key={index}>{String(timelineStartHour + index).padStart(2, "0")}:00</div>)}
                </div>
                <div className="grid flex-1" style={{ gridTemplateColumns: `repeat(${Math.max(1, dailyColumns.length)}, minmax(220px, 1fr))` }}>
                  {dailyColumns.map((member) => {
                    const memberSchedules = schedulesFor(member.id, selectedDay);
                    const memberExceptions = exceptionsFor(member.id, selectedDay);
                    const memberBookings = bookingsFor(member.id, selectedDay);
                    const fullDayUnavailable = memberExceptions.some((item) => item.is_unavailable);
                    return (
                      <div key={member.id} className="relative border-r border-line/50 bg-[#fcfdfe]/40 p-2 last:border-r-0">
                        {memberSchedules.map((item) => (
                          <div key={item.id} className="absolute inset-x-2 rounded-xl border border-action/10 bg-[#e8efe9]" style={blockStyle(timeToMinutes(item.start_time), timeToMinutes(item.end_time))} />
                        ))}
                        {fullDayUnavailable && <div className="availability-stripes absolute inset-x-3 bottom-2 top-2 z-10 rounded-xl border border-line/70 opacity-70" />}
                        {memberExceptions.filter((item) => !item.is_unavailable && item.start_time && item.end_time).map((item) => (
                          <div key={item.id} className="availability-stripes absolute inset-x-3 z-20 flex items-center justify-center rounded-lg border border-line/70" style={blockStyle(timeToMinutes(item.start_time!), timeToMinutes(item.end_time!))}>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-ink/45">Exception</span>
                          </div>
                        ))}
                        {memberBookings.map((booking) => (
                          <div key={booking.id} className="absolute inset-x-3 z-30 rounded-lg border border-action bg-action p-3 text-white shadow-sm" style={blockStyle(dateTimeToLocalMinutes(booking.start_time), dateTimeToLocalMinutes(booking.end_time))}>
                            <span className="block truncate text-xs font-bold">{booking.client_name}</span>
                            <span className="mt-0.5 block text-[10px] font-medium text-white/75">{new Date(booking.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - {new Date(booking.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="min-w-[840px]">
              <div className="flex border-b border-line/60 bg-[#f4f6f5]/50 py-4">
                <div className="w-24 shrink-0 text-center text-[11px] font-bold uppercase tracking-wider text-ink/55">Time</div>
                <div className="grid flex-1 grid-cols-5 text-center text-xs font-bold text-ink">
                  {weekDays.map((day) => (
                    <div key={dateInputValue(day)} className="border-r border-line/50 last:border-r-0">
                      <span className="block text-[10px] font-medium uppercase text-ink/55">{days[(day.getDay() + 6) % 7]}</span>
                      <span className="mt-0.5 block text-sm">{dateLabel(day)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="relative flex h-[630px]">
                <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
                  {Array.from({ length: 10 }).map((_, index) => <div key={index} className="h-0 w-full border-b border-line/60" />)}
                </div>
                <div className="z-10 flex w-24 shrink-0 flex-col justify-between border-r border-line/70 bg-[#fcfdfe] py-2 text-center text-[11px] font-bold text-ink/55">
                  {Array.from({ length: 10 }).map((_, index) => <div key={index}>{String(timelineStartHour + index).padStart(2, "0")}:00</div>)}
                </div>
                <div className="grid flex-1 grid-cols-5">
                  {weekDays.map((day) => {
                    const targetStaff = selectedStaffId || staff[0]?.id || "";
                    const daySchedules = targetStaff ? schedulesFor(targetStaff, day) : [];
                    const dayExceptions = targetStaff ? exceptionsFor(targetStaff, day) : [];
                    const dayBookings = targetStaff ? bookingsFor(targetStaff, day) : [];
                    return (
                      <div key={dateInputValue(day)} className="relative border-r border-line/50 bg-[#fcfdfe]/40 p-2 last:border-r-0">
                        {daySchedules.map((item) => (
                          <div key={item.id} className="absolute inset-x-2 rounded-xl border border-action/10 bg-[#e8efe9]" style={blockStyle(timeToMinutes(item.start_time), timeToMinutes(item.end_time))} />
                        ))}
                        {dayExceptions.some((item) => item.is_unavailable) && <div className="availability-stripes absolute inset-x-3 bottom-2 top-2 z-10 rounded-xl border border-line/70 opacity-70" />}
                        {dayBookings.map((booking) => (
                          <div key={booking.id} className="absolute inset-x-3 z-30 rounded-lg border border-action bg-action p-2.5 text-white shadow-sm" style={blockStyle(dateTimeToLocalMinutes(booking.start_time), dateTimeToLocalMinutes(booking.end_time))}>
                            <span className="block truncate text-xs font-bold">{booking.client_name}</span>
                            <span className="mt-0.5 block text-[10px] font-medium text-white/75">{new Date(booking.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
              <p className="border-t border-line/60 bg-[#fcfdfe] px-5 py-3 text-xs font-medium text-ink/55">
                Weekly grid is showing {selectedStaffId ? selectedStaffName : staff[0]?.name || "the first staff member"}. Pick a staff member above to inspect their week.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <button type="button" onClick={() => setActiveEditor("schedule")} className="dashboard-card grid min-h-[7rem] gap-2 border-white bg-white p-5 text-left text-ink shadow-[0_20px_40px_rgba(14,71,49,0.03)] hover:bg-[#fcfdfe]">
          <span className="eyebrow">Weekly hours</span>
          <span className="text-lg font-semibold">Set working hours</span>
          <span className="muted">{activeSchedules} saved window{activeSchedules === 1 ? "" : "s"}</span>
        </button>
        <button type="button" onClick={() => setActiveEditor("exception")} className="dashboard-card grid min-h-[7rem] gap-2 border-white bg-white p-5 text-left text-ink shadow-[0_20px_40px_rgba(14,71,49,0.03)] hover:bg-[#fcfdfe]">
          <span className="eyebrow">Exceptions</span>
          <span className="text-lg font-semibold">Block time</span>
          <span className="muted">{upcomingExceptions.length} upcoming exception{upcomingExceptions.length === 1 ? "" : "s"}</span>
        </button>
        <div className="dashboard-card grid min-h-[7rem] gap-2 p-5">
          <span className="eyebrow">Current view</span>
          <span className="text-lg font-semibold">{selectedStaffName}</span>
          <span className="muted">{viewMode === "timeline" ? dateLabel(selectedDay, true) : `${dateLabel(weekStart)} - ${dateLabel(addDays(weekStart, 4))}`}</span>
        </div>
      </section>

      {activeEditor && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 px-4 py-8 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-white bg-white p-6 shadow-[0_30px_80px_rgba(14,71,49,0.18)]">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">{activeEditor === "schedule" ? "Weekly hours" : "Exceptions"}</p>
                <h2 className="section-title mt-1">{activeEditor === "schedule" ? "Set working hours" : "Block time"}</h2>
                <p className="muted mt-1">
                  {activeEditor === "schedule"
                    ? "Choose who is working, the day, and the hours they can take bookings."
                    : "Choose a date or time that should not be available for booking."}
                </p>
              </div>
              <button type="button" onClick={() => setActiveEditor(null)} className="secondary-button min-h-0 rounded-xl px-3 py-2 text-xs">Close</button>
            </div>

            {activeEditor === "schedule" ? (
              <form onSubmit={addSchedule} className="grid gap-4">
                <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                  Apply to
                  <select name="staff_id">
                    <option value="">All staff</option>
                    {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                  </select>
                </label>
                <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                  Repeats every
                  <select name="day_of_week" required>
                    {days.map((day, index) => <option key={day} value={index}>{day}</option>)}
                  </select>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                    Starts
                    <input name="start_time" type="time" required />
                  </label>
                  <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                    Ends
                    <input name="end_time" type="time" required />
                  </label>
                </div>
                <button type="submit">Save working hours</button>
              </form>
            ) : (
              <form onSubmit={addException} className="grid gap-4">
                <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                  Apply to
                  <select name="staff_id">
                    <option value="">All staff - business-wide exception</option>
                    {staff.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                  </select>
                </label>
                <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                  Date
                  <input name="date" type="date" defaultValue={selectedDate} required />
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                    Starts
                    <input name="start_time" type="time" disabled={exceptionUnavailable} />
                  </label>
                  <label className="grid gap-2 text-xs font-bold uppercase tracking-wider text-ink/55">
                    Ends
                    <input name="end_time" type="time" disabled={exceptionUnavailable} />
                  </label>
                </div>
                <label className="flex items-center justify-between rounded-xl border border-line/70 bg-[#fcfdfe] px-3 py-2 text-sm font-semibold">
                  Full day unavailable
                  <input className="h-4 w-4 accent-[#0e4731]" name="is_unavailable" type="checkbox" checked={exceptionUnavailable} onChange={(event) => setExceptionUnavailable(event.target.checked)} />
                </label>
                <input name="reason" placeholder="Note, e.g. public holiday" />
                <button type="submit">Block time</button>
              </form>
            )}
          </div>
        </div>
      )}
      {error && <p className="text-sm text-red-700">{error}</p>}
    </DashboardShell>
  );
}
