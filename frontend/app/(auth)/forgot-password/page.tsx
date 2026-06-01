"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";
import { AuthShell } from "../../../components/AuthShell";

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await api.forgotPassword({ email: form.get("email") });
      setMessage("If an account exists, a reset link has been sent to your email.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request reset");
    }
  }

  return (
    <AuthShell
      eyebrow="Booking Scheduler"
      title="Keep bookings, deposits, quotes, and client notes moving."
      description="Sign in to manage services, staff availability, booking status, inspo uploads, and payment records."
      switchHref="/login"
      switchLabel="Back to login"
      formTitle="Reset password"
      formSubtitle="We'll send you a reset link."
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

        {message && (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            {message}
          </p>
        )}

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </p>
        )}

        <button
          className="auth-submit mt-1"
          type="submit"
        >
          Send Reset Link
        </button>

        <div className="text-center">
          <Link
            href="/login"
            className="text-sm font-semibold text-slate-600 hover:text-emerald-700"
          >
            Remember your password? Sign in
          </Link>
        </div>
      </form>
    </AuthShell>
  );
}
