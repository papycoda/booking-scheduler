"use client";

import { FormEvent, useState } from "react";
import { api } from "../../../lib/api";

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
      localStorage.setItem("access_token", response.access_token);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to login");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <form onSubmit={submit} className="grid w-full gap-4">
        <h1 className="text-3xl font-semibold">Login</h1>
        <input name="email" type="email" placeholder="Email" required />
        <input name="password" type="password" placeholder="Password" required />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button type="submit">Login</button>
      </form>
    </main>
  );
}
