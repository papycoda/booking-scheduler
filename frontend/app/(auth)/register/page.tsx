"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, getAccessToken, storeAccessToken } from "../../../lib/api";
import { AuthShell } from "../../../components/AuthShell";

export default function RegisterPage() {
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (getAccessToken()) window.location.replace("/dashboard");
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    try {
      const response = await api.register({
        business_name: form.get("business_name"),
        full_name: form.get("full_name"),
        email: form.get("email"),
        password: form.get("password"),
      });
      storeAccessToken(response.access_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to register");
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Booking Scheduler"
      title="Run deposits, bookings, staff, and client intake from one dashboard."
      description="Create your business account, publish a booking link, collect deposits, and let clients choose available times without signing up."
      switchHref="/login"
      switchLabel="Login"
      formTitle="Create account"
      formSubtitle="For business owners and staff managers."
    >
      <form onSubmit={submit} className="grid gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="auth-label">
            Business name
            <input
              className="auth-input"
              name="business_name"
              placeholder="Studio Ayo"
              required
            />
          </label>
          <label className="auth-label">
            Your name
            <input
              className="auth-input"
              name="full_name"
              placeholder="Yemi Ade"
              required
            />
          </label>
        </div>
        <label className="auth-label">
          Email address
          <input
            className="auth-input"
            name="email"
            type="email"
            placeholder="owner@example.com"
            required
          />
        </label>
        <label className="auth-label">
          Password
          <input
            className="auth-input"
            name="password"
            type="password"
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </label>

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </p>
        )}

        <button
          className="auth-submit mt-1"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
