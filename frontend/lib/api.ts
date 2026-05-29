const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ApiOptions = RequestInit & { token?: string };

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail?.message ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type Service = {
  id: string;
  name: string;
  description?: string | null;
  duration_minutes: number;
  price: number;
  currency: string;
  pricing_mode: "fixed" | "from" | "consultation";
  deposit_policy: "tenant_default" | "custom" | "disabled";
  deposit_amount?: number | null;
  deposit_due_now?: number;
  price_label?: string;
  is_active: boolean;
};

export type Staff = {
  id: string;
  name: string;
  bio?: string | null;
  avatar_url?: string | null;
  is_bookable: boolean;
  is_active: boolean;
};

export type Tenant = {
  id?: string;
  slug: string;
  name: string;
  description?: string | null;
  logo_url?: string | null;
  timezone: string;
  phone?: string | null;
  address?: string | null;
  paystack_subaccount_code?: string | null;
  paystack_business_name?: string | null;
  platform_fee_percentage?: string;
  allow_staff_selection: boolean;
  booking_buffer_minutes?: number;
  default_deposit_amount?: number;
  advance_booking_days: number;
  min_notice_hours?: number;
  cancellation_notice_hours?: number;
  status?: string;
};

export type Slot = {
  start_time: string;
  end_time: string;
};

export type DashboardBooking = {
  id: string;
  status: string;
  start_time: string;
  end_time: string;
  client_name: string;
  client_email: string;
  service_name: string;
  staff_name: string;
  amount?: number | null;
  payment_status?: string | null;
  deposit_amount: number;
  price_status: string;
  quoted_price?: number | null;
  client_notes?: string | null;
  inspo_assets?: Array<{ id: string; original_filename: string; content_type: string; size_bytes: number; url: string }>;
};

export type AvailabilitySchedule = {
  id: string;
  staff_id?: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_active: boolean;
};

export type AvailabilityOverride = {
  id: string;
  staff_id?: string | null;
  date: string;
  is_unavailable: boolean;
  start_time?: string | null;
  end_time?: string | null;
  reason?: string | null;
};

export type AnalyticsOverview = {
  from_date: string;
  to_date: string;
  bookings_count: number;
  revenue: number;
  top_services: Array<{ name: string; count: number }>;
};

export function getAccessToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("access_token") ?? "";
}

export const api = {
  register: (body: unknown) => request<{ access_token: string; slug: string }>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: unknown) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  forgotPassword: (body: unknown) => request<{ status: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify(body) }),
  resetPassword: (body: unknown) => request<{ status: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify(body) }),
  tenant: (slug: string) => request<Tenant>(`/book/${slug}`),
  services: (slug: string) => request<Service[]>(`/book/${slug}/services`),
  staff: (slug: string, serviceId: string) => request<Staff[]>(`/book/${slug}/staff?service_id=${serviceId}`),
  slots: (slug: string, serviceId: string, date: string, staffId?: string) => {
    const params = new URLSearchParams({ service_id: serviceId, date });
    if (staffId) params.set("staff_id", staffId);
    return request<Slot[]>(`/book/${slug}/slots?${params}`);
  },
  createBooking: (slug: string, body: unknown) =>
    request<{ booking_id: string; payment_url: string; reference: string; expires_at: string; deposit_amount: number }>(`/book/${slug}/bookings`, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  bookingStatus: (slug: string, bookingId: string) => request<unknown>(`/book/${slug}/bookings/${bookingId}/status`),
  dashboardBookings: (token = getAccessToken()) => request<DashboardBooking[]>("/dashboard/bookings", { token }),
  dashboardAnalytics: (token = getAccessToken()) => request<AnalyticsOverview>("/dashboard/analytics/overview", { token }),
  updateDashboardBooking: (bookingId: string, body: unknown, token = getAccessToken()) =>
    request<DashboardBooking>(`/dashboard/bookings/${bookingId}`, { method: "PATCH", body: JSON.stringify(body), token }),
  currentTenant: (token = getAccessToken()) => request<Tenant>("/tenants/me", { token }),
  updateTenant: (body: unknown, token = getAccessToken()) => request<Tenant>("/tenants/me", { method: "PATCH", body: JSON.stringify(body), token }),
  paystackStatus: (token = getAccessToken()) =>
    request<{ paystack_subaccount_code?: string | null; paystack_business_name?: string | null; onboarded: boolean }>("/tenants/me/paystack", { token }),
  onboardPaystack: (body: unknown, token = getAccessToken()) =>
    request<{ paystack_subaccount_code?: string | null; paystack_business_name?: string | null; onboarded: boolean }>("/tenants/me/paystack", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),
  dashboardServices: (token = getAccessToken()) => request<Service[]>("/services", { token }),
  createService: (body: unknown, token = getAccessToken()) => request<Service>("/services", { method: "POST", body: JSON.stringify(body), token }),
  updateService: (serviceId: string, body: unknown, token = getAccessToken()) =>
    request<Service>(`/services/${serviceId}`, { method: "PATCH", body: JSON.stringify(body), token }),
  deleteService: (serviceId: string, token = getAccessToken()) => request<void>(`/services/${serviceId}`, { method: "DELETE", token }),
  dashboardStaff: (token = getAccessToken()) => request<Staff[]>("/staff", { token }),
  createStaff: (body: unknown, token = getAccessToken()) => request<Staff>("/staff", { method: "POST", body: JSON.stringify(body), token }),
  updateStaff: (staffId: string, body: unknown, token = getAccessToken()) =>
    request<Staff>(`/staff/${staffId}`, { method: "PATCH", body: JSON.stringify(body), token }),
  deleteStaff: (staffId: string, token = getAccessToken()) => request<void>(`/staff/${staffId}`, { method: "DELETE", token }),
  assignStaffServices: (staffId: string, serviceIds: string[], token = getAccessToken()) =>
    request<void>(`/staff/${staffId}/services`, { method: "POST", body: JSON.stringify({ service_ids: serviceIds }), token }),
  schedules: (token = getAccessToken()) => request<AvailabilitySchedule[]>("/availability/schedules", { token }),
  createSchedule: (body: unknown, token = getAccessToken()) =>
    request<AvailabilitySchedule>("/availability/schedules", { method: "POST", body: JSON.stringify(body), token }),
  deleteSchedule: (scheduleId: string, token = getAccessToken()) => request<void>(`/availability/schedules/${scheduleId}`, { method: "DELETE", token }),
  overrides: (from: string, to: string, token = getAccessToken()) =>
    request<AvailabilityOverride[]>(`/availability/overrides?from=${from}&to=${to}`, { token }),
  createOverride: (body: unknown, token = getAccessToken()) =>
    request<AvailabilityOverride>("/availability/overrides", { method: "POST", body: JSON.stringify(body), token }),
  deleteOverride: (overrideId: string, token = getAccessToken()) => request<void>(`/availability/overrides/${overrideId}`, { method: "DELETE", token }),
};
