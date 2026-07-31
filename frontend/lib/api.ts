const configuredApiBaseUrl = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");
const API_BASE_URL = configuredApiBaseUrl.endsWith("/api/v1")
  ? configuredApiBaseUrl
  : `${configuredApiBaseUrl}/api/v1`;

type ApiOptions = RequestInit & { token?: string };

export type ApiFieldError = {
  field: string;
  message: string;
};

export class ApiError extends Error {
  code?: string;
  fieldErrors: ApiFieldError[];

  constructor(message: string, code?: string, fieldErrors: ApiFieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.fieldErrors = fieldErrors;
  }
}

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
    if ((response.status === 401 || response.status === 403) && options.token && typeof window !== "undefined") {
      clearAccessToken();
      const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
      window.location.replace(`/login?next=${next}`);
    }
    const detail = body?.detail;
    const errorBody = typeof detail === "object" && detail !== null ? detail : body;
    const message =
      (typeof errorBody?.message === "string" && errorBody.message) ||
      (typeof detail === "string" ? detail : "Request failed");
    const code = typeof errorBody?.error === "string" ? errorBody.error : undefined;
    const fieldErrors = Array.isArray(errorBody?.fields)
      ? errorBody.fields.filter((item: unknown): item is ApiFieldError => {
          return (
            typeof item === "object" &&
            item !== null &&
            typeof (item as ApiFieldError).field === "string" &&
            typeof (item as ApiFieldError).message === "string"
          );
        })
      : [];
    throw new ApiError(message, code, fieldErrors);
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
  service_ids?: string[];
};

export type Tenant = {
  id?: string;
  slug: string;
  name: string;
  description?: string | null;
  logo_url?: string | null;
  timezone: string;
  phone?: string | null;
  whatsapp_number?: string | null;
  address?: string | null;
  front_desk_intro?: string | null;
  front_desk_hours?: string | null;
  front_desk_service_areas?: string | null;
  front_desk_prep_notes?: string | null;
  front_desk_policies?: string | null;
  front_desk_escalation_rules?: string | null;
  payout_bank_name?: string | null;
  payout_account_name?: string | null;
  masked_payout_account_number?: string | null;
  payment_setup_status?: string;
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

export type AssistantAction = {
  type: "view_service" | "book_now" | "show_slots";
  label: string;
  service_id?: string | null;
  start_time?: string | null;
};

export type AssistantRequest = {
  message: string;
  context?: {
    service_id?: string | null;
    selected_date?: string | null;
  } | null;
};

export type AssistantResponse = {
  reply: string;
  intent:
    | "list_services"
    | "service_price"
    | "service_duration"
    | "available_slots"
    | "business_location"
    | "deposit_policy"
    | "cancellation_policy"
    | "reschedule_policy"
    | "how_to_book"
    | "fallback";
  suggested_actions: AssistantAction[];
};

export type WhatsAppConversation = {
  id: string;
  tenant_id: string;
  customer_phone: string;
  customer_name?: string | null;
  state: string;
  status: string;
  summary?: string | null;
  last_message_at?: string | null;
  last_inbound_at?: string | null;
  last_outbound_at?: string | null;
  booking_id?: string | null;
  assigned_user_id?: string | null;
};

export type WhatsAppMessage = {
  id: string;
  direction: string;
  author_type: string;
  body: string;
  status: string;
  provider_message_id?: string | null;
  sent_at?: string | null;
  created_at: string;
};

export type WhatsAppConversationDetail = WhatsAppConversation & {
  booking_context: Record<string, unknown>;
  messages: WhatsAppMessage[];
};

export type DashboardBooking = {
  id: string;
  payment_id?: string | null;
  status: string;
  start_time: string;
  end_time: string;
  client_name: string;
  client_email: string;
  service_name: string;
  staff_name: string;
  amount?: number | null;
  payment_status?: string | null;
  collection_mode?: string | null;
  platform_fee_amount?: number | null;
  business_net_amount?: number | null;
  settlement_status?: string | null;
  deposit_amount: number;
  price_status: string;
  quoted_price?: number | null;
  client_notes?: string | null;
  cancellation_reason?: string | null;
  cancelled_by?: string | null;
  inspo_assets?: Array<{ id: string; original_filename: string; content_type: string; size_bytes: number; url: string }>;
};

export type ManagedBooking = {
  booking_id: string;
  booking_status: string;
  payment_status?: string | null;
  payment_url?: string | null;
  start_time: string;
  end_time: string;
  service_id: string;
  service_name: string;
  staff_id: string;
  staff_name: string;
  deposit_amount: number;
  price_status: string;
  quoted_price?: number | null;
  cancellation_deadline: string;
  can_cancel: boolean;
  deposit_notice: string;
  pending_reschedule_requests: RescheduleRequest[];
};

export type RescheduleRequest = {
  id: string;
  status: string;
  requested_start_time: string;
  requested_end_time: string;
  requested_staff_id: string;
  staff_name?: string | null;
  hold_expires_at: string;
  client_note?: string | null;
  decision_note?: string | null;
};

export type DashboardRescheduleRequest = {
  id: string;
  booking_id: string;
  status: string;
  client_name: string;
  client_email: string;
  service_name: string;
  current_staff_name: string;
  requested_staff_name: string;
  current_start_time: string;
  current_end_time: string;
  requested_start_time: string;
  requested_end_time: string;
  hold_expires_at: string;
  client_note?: string | null;
  decision_note?: string | null;
};

export type PaymentSetupStatus = {
  payout_bank_name?: string | null;
  payout_account_name?: string | null;
  masked_payout_account_number?: string | null;
  payment_setup_status: string;
  payments_enabled: boolean;
  payout_ready: boolean;
  onboarded: boolean;
  warning_message?: string | null;
};

export type DashboardPayout = {
  payment_id: string;
  settlement_status: string;
  payout_transfer_reference?: string | null;
  payout_transfer_code?: string | null;
};

export type DashboardPayoutDetail = DashboardPayout & {
  booking_id: string;
  client_name: string;
  service_name: string;
  amount: number;
  platform_fee_amount: number;
  business_net_amount: number;
  payout_attempt_count: number;
  payout_review_reason?: string | null;
  last_payout_error?: string | null;
  next_payout_attempt_at?: string | null;
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

export function storeAccessToken(accessToken: string) {
  localStorage.setItem("access_token", accessToken);
  document.cookie = "dashboard_session=1; path=/; max-age=604800; samesite=lax";
}

export function clearAccessToken() {
  localStorage.removeItem("access_token");
  document.cookie = "dashboard_session=; path=/; max-age=0; samesite=lax";
}

export function apiAssetUrl(url: string) {
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE_URL.replace(/\/$/, "")}${url.startsWith("/") ? url : `/${url}`}`;
}

export function koboToNgn(amount?: number | null) {
  return (amount ?? 0) / 100;
}

export function ngnToKobo(value: FormDataEntryValue | null) {
  const amount = Number(value || 0);
  return Math.round(amount * 100);
}

export function formatNgn(amount?: number | null) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(koboToNgn(amount));
}

export function bookingStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    confirmed: "Booked",
    pending_payment: "Needs payment",
    completed: "Done",
    cancelled: "Cancelled",
    no_show: "No show",
    expired: "Expired",
  };
  return labels[status ?? ""] ?? "Booked";
}

export function paymentStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    paid: "Deposit paid",
    success: "Deposit paid",
    pending: "Waiting for payment",
    failed: "Payment failed",
  };
  return labels[status ?? ""] ?? "Waiting for payment";
}

export function payoutStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    paid: "Payout sent",
    pending: "Payout pending",
    queued: "Payout pending",
    processing: "Sending payout",
    needs_review: "Needs review",
    needs_setup: "Bank details needed",
    failed: "Payout failed",
    not_due: "Not ready yet",
  };
  return labels[status ?? ""] ?? "Not ready yet";
}

export function priceModeLabel(mode?: Service["pricing_mode"]) {
  if (mode === "from") return "Starts from";
  if (mode === "consultation") return "Quote after details";
  return "Fixed price";
}

export function depositPolicyLabel(policy?: Service["deposit_policy"]) {
  if (policy === "custom") return "Different deposit";
  if (policy === "disabled") return "Full payment now";
  return "Normal deposit";
}

export const api = {
  register: (body: unknown) => request<{ access_token: string; slug: string }>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: unknown) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  forgotPassword: (body: unknown) => request<{ status: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify(body) }),
  resetPassword: (body: unknown) => request<{ status: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify(body) }),
  tenant: (slug: string) => request<Tenant>(`/book/${slug}`),
  services: (slug: string) => request<Service[]>(`/book/${slug}/services`),
  assistant: (slug: string, body: AssistantRequest) =>
    request<AssistantResponse>(`/book/${slug}/assistant`, { method: "POST", body: JSON.stringify(body) }),
  staff: (slug: string, serviceId: string) => request<Staff[]>(`/book/${slug}/staff?service_id=${serviceId}`),
  slots: (slug: string, serviceId: string, date: string, staffId?: string) => {
    const params = new URLSearchParams({ service_id: serviceId, date });
    if (staffId) params.set("staff_id", staffId);
    return request<Slot[]>(`/book/${slug}/slots?${params}`);
  },
  createBooking: (slug: string, body: unknown) =>
    request<{ booking_id: string; payment_url?: string | null; reference: string; expires_at: string; deposit_amount: number; manage_url: string; payment_pending?: boolean; payment_message?: string | null }>(`/book/${slug}/bookings`, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  bookingStatus: (slug: string, bookingId: string, token?: string) =>
    request<{ booking_status?: string; manage_url?: string | null }>(`/book/${slug}/bookings/${bookingId}/status${token ? `?token=${encodeURIComponent(token)}` : ""}`),
  managedBooking: (slug: string, bookingId: string, token: string) =>
    request<ManagedBooking>(`/book/${slug}/bookings/${bookingId}/manage?token=${encodeURIComponent(token)}`),
  cancelManagedBooking: (slug: string, bookingId: string, token: string, reason?: string) =>
    request<void>(`/book/${slug}/bookings/${bookingId}/cancel?token=${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
    }),
  rescheduleSlots: (slug: string, bookingId: string, token: string, date: string, staffId?: string) => {
    const params = new URLSearchParams({ token, date });
    if (staffId) params.set("staff_id", staffId);
    return request<Slot[]>(`/book/${slug}/bookings/${bookingId}/reschedule-slots?${params}`);
  },
  createRescheduleRequest: (slug: string, bookingId: string, token: string, body: unknown) =>
    request<RescheduleRequest>(`/book/${slug}/bookings/${bookingId}/reschedule-requests?token=${encodeURIComponent(token)}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dashboardBookings: (token = getAccessToken()) => request<DashboardBooking[]>("/dashboard/bookings", { token }),
  dashboardRescheduleRequests: (token = getAccessToken()) => request<DashboardRescheduleRequest[]>("/dashboard/reschedule-requests", { token }),
  whatsappConversations: (status?: string, token = getAccessToken()) =>
    request<WhatsAppConversation[]>(`/dashboard/whatsapp/conversations${status ? `?status_filter=${encodeURIComponent(status)}` : ""}`, { token }),
  whatsappConversation: (conversationId: string, token = getAccessToken()) =>
    request<WhatsAppConversationDetail>(`/dashboard/whatsapp/conversations/${conversationId}`, { token }),
  whatsappClaimConversation: (conversationId: string, token = getAccessToken()) =>
    request<WhatsAppConversation>(`/dashboard/whatsapp/conversations/${conversationId}/claim`, { method: "POST", token }),
  whatsappReplyConversation: (conversationId: string, body: { body: string }, token = getAccessToken()) =>
    request<{ conversation_id: string; message_id: string; status: string }>(`/dashboard/whatsapp/conversations/${conversationId}/reply`, {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),
  decideRescheduleRequest: (requestId: string, body: unknown, token = getAccessToken()) =>
    request<void>(`/dashboard/reschedule-requests/${requestId}/decision`, { method: "POST", body: JSON.stringify(body), token }),
  dashboardAnalytics: (token = getAccessToken()) => request<AnalyticsOverview>("/dashboard/analytics/overview", { token }),
  updateDashboardBooking: (bookingId: string, body: unknown, token = getAccessToken()) =>
    request<DashboardBooking>(`/dashboard/bookings/${bookingId}`, { method: "PATCH", body: JSON.stringify(body), token }),
  initiateDashboardPayout: (paymentId: string, token = getAccessToken()) =>
    request<DashboardPayout>(`/dashboard/payments/${paymentId}/payout`, { method: "POST", token }),
  dashboardPayouts: (token = getAccessToken()) => request<DashboardPayoutDetail[]>("/dashboard/payouts", { token }),
  approveDashboardPayout: (paymentId: string, token = getAccessToken()) =>
    request<DashboardPayout>(`/dashboard/payouts/${paymentId}/approve`, { method: "POST", token }),
  retryDashboardPayout: (paymentId: string, token = getAccessToken()) =>
    request<DashboardPayout>(`/dashboard/payouts/${paymentId}/retry`, { method: "POST", token }),
  currentTenant: (token = getAccessToken()) => request<Tenant>("/tenants/me", { token }),
  updateTenant: (body: unknown, token = getAccessToken()) => request<Tenant>("/tenants/me", { method: "PATCH", body: JSON.stringify(body), token }),
  paystackStatus: (token = getAccessToken()) =>
    request<PaymentSetupStatus>("/tenants/me/paystack", { token }),
  savePayoutSetup: (body: unknown, token = getAccessToken()) =>
    request<PaymentSetupStatus>("/tenants/me/payout-setup", { method: "POST", body: JSON.stringify(body), token }),
  onboardPaystack: (body: unknown, token = getAccessToken()) =>
    request<PaymentSetupStatus>("/tenants/me/paystack", {
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
