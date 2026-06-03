"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { api, getAccessToken, storeAccessToken } from "../../../lib/api";
import { AuthShell } from "../../../components/AuthShell";

export default function LoginPage() {
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
      const response = await api.login({
        email: form.get("email"),
        password: form.get("password"),
      });
      storeAccessToken(response.access_token);
      const next = new URLSearchParams(window.location.search).get("next") || "/dashboard";
      window.location.href = next;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to login");
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Booking Scheduler"
      title="Keep bookings, deposits, quotes, and client notes moving."
      description="Sign in to manage services, staff availability, booking status, inspo uploads, and payment records."
      switchHref="/register"
      switchLabel="Register"
      formTitle="Welcome back"
      formSubtitle="Access your business dashboard."
    >
      <form onSubmit={submit} className="grid gap-4">
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
            placeholder="Your password"
            required
          />
        </label>

        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
          >
            Forgot password?
          </Link>
        </div>

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
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}
