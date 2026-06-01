"use client";

import { FormEvent, useState } from "react";
import { api, storeAccessToken } from "../../../lib/api";

export default function RegisterPage() {
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
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
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <form onSubmit={submit} className="panel grid w-full gap-4">
        <div>
          <p className="eyebrow">Start booking</p>
          <h1 className="mt-1 text-3xl font-semibold">Create account</h1>
        </div>
        <input name="business_name" placeholder="Business name" required />
        <input name="full_name" placeholder="Your name" required />
        <input name="email" type="email" placeholder="Email" required />
        <input name="password" type="password" placeholder="Password" minLength={8} required />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit">Register</button>
      </form>
    </main>
  );
}
