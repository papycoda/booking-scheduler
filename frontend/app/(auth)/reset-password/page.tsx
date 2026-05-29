"use client";

import { FormEvent, useState } from "react";
import { api } from "../../../lib/api";

export default function ResetPasswordPage({ searchParams }: { searchParams: { token?: string } }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api.resetPassword({
        token: searchParams.token ?? form.get("token"),
        new_password: form.get("new_password"),
      });
      setMessage("Password updated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset password");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <form onSubmit={submit} className="grid w-full gap-4">
        <h1 className="text-3xl font-semibold">Reset Password</h1>
        {!searchParams.token && <input name="token" placeholder="Reset token" required />}
        <input name="new_password" type="password" placeholder="New password" minLength={8} required />
        {message && <p className="text-sm text-action">{message}</p>}
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit">Update Password</button>
      </form>
    </main>
  );
}
