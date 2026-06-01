"use client";

import { FormEvent, useState } from "react";
import { api } from "../../../lib/api";

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api.forgotPassword({ email: form.get("email") });
      setMessage("If an account exists, a reset link has been sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request reset");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <form onSubmit={submit} className="panel grid w-full gap-4">
        <div>
          <p className="eyebrow">Account access</p>
          <h1 className="mt-1 text-3xl font-semibold">Forgot password</h1>
        </div>
        <input name="email" type="email" placeholder="Email" required />
        {message && <p className="text-sm text-action">{message}</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit">Send Reset Link</button>
      </form>
    </main>
  );
}
