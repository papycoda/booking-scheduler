"use client";

import { FormEvent, useState } from "react";
import { api, storeAccessToken } from "../../../lib/api";

export default function LoginPage() {
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await api.login({
        email: form.get("email"),
        password: form.get("password"),
      });
      storeAccessToken(response.access_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to login");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <form onSubmit={submit} className="panel grid w-full gap-4">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h1 className="mt-1 text-3xl font-semibold">Login</h1>
        </div>
        <input name="email" type="email" placeholder="Email" required />
        <input name="password" type="password" placeholder="Password" required />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit">Login</button>
      </form>
    </main>
  );
}
