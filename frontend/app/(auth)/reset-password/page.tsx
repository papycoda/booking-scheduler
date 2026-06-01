"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { api } from "../../../lib/api";
import { AuthShell } from "../../../components/AuthShell";

export default function ResetPasswordPage({ searchParams }: { searchParams: { token?: string } }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const hasToken = searchParams.token;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    try {
      await api.resetPassword({
        token: searchParams.token ?? form.get("token"),
        new_password: form.get("new_password"),
      });
      setMessage("Password updated successfully. You can now sign in with your new password.");
      setIsSubmitting(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset password");
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Booking Scheduler"
      title="Keep bookings, deposits, quotes, and client notes moving."
      description="Sign in to manage services, staff availability, booking status, inspo uploads, and payment records."
      switchHref="/login"
      switchLabel="Back to login"
      formTitle="Set new password"
      formSubtitle="Choose a secure password for your account."
    >
      <form onSubmit={submit} className="grid gap-4">
        {!hasToken && (
          <label className="auth-label">
            Reset token
            <input
              className="auth-input"
              name="token"
              placeholder="Paste your reset token here"
              required
            />
          </label>
        )}

        <label className="auth-label">
          New password
          <input
            className="auth-input"
            name="new_password"
            type="password"
            placeholder="At least 8 characters"
            minLength={8}
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
          disabled={isSubmitting}
        >
          {isSubmitting ? "Updating..." : "Update Password"}
        </button>

        <div className="text-center">
          <Link
            href="/login"
            className="text-sm font-semibold text-slate-600 hover:text-emerald-700"
          >
            Back to sign in
          </Link>
        </div>
      </form>
    </AuthShell>
  );
}
