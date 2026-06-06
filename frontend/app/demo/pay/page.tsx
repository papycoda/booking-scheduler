"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function completeDemoPayment(reference: string, token: string) {
  const query = new URLSearchParams({ reference, token });
  const response = await fetch(`${API_BASE_URL}/webhooks/demo/complete-payment?${query}`, {
    method: "POST",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "Payment failed" }));
    throw new Error(error.message || "Payment failed");
  }
  return response.json();
}

function formatNgn(amount: number) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(amount);
}

function DemoPaymentContent() {
  const searchParams = useSearchParams();
  const reference = searchParams.get("reference") || "";
  const token = searchParams.get("token") || "";
  const manageToken = searchParams.get("manage_token") || "";
  const slug = searchParams.get("slug") || "";
  const bookingId = searchParams.get("booking_id") || "";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // Handle direct navigation with params (from modified demo URL)
  useEffect(() => {
    if (success && slug && bookingId) {
      const query = new URLSearchParams({ booking_id: bookingId });
      if (manageToken) query.set("token", manageToken);
      window.location.href = `/book/${slug}/verify?${query}`;
    }
  }, [success, slug, bookingId, manageToken]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(false);

    try {
      await completeDemoPayment(reference, token);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to complete demo payment");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f5f8f6] px-5 py-10 text-ink">
      <section className="public-glass grid w-full max-w-md justify-items-center gap-6 p-8">
        <div className="grid place-items-center gap-3">
          <div className="grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-[#0e4731] to-[#1b5e43] text-white shadow-md">
            <svg className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 2c0 3.866-4 7-9 7s-9-3.134-9-7 4-7 9-7 9 3.134 9 7zm0 0c0 3.866 4 7 9 7s9-3.134 9-7m-9 7a4 4 0 01-4-4c0-1.866 4-4 9-4 9 2.134 4 4-4 4-4 4-4-9-7-9-7z" />
            </svg>
          </div>
          <div>
            <p className="eyebrow mx-auto">Demo Payment</p>
            <h1 className="mt-2 text-2xl font-bold tracking-normal">Complete Test Payment</h1>
          </div>
        </div>

        <p className="text-center text-sm font-medium text-ink/70">
          This is a demo payment page for testing purposes. No real money will be charged.
        </p>

        {success ? (
          <div className="grid gap-3 text-center">
            <div className="grid h-16 w-16 place-items-center rounded-full bg-green-100 mx-auto">
              <svg className="h-8 w-8 text-green-700" fill="none" stroke="currentColor" strokeWidth="2.4" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <p className="font-semibold text-action">Payment completed!</p>
            <p className="text-sm text-ink/65">Redirecting to verification page...</p>
          </div>
        ) : (
          <form onSubmit={submit} className="grid gap-4">
            <div className="rounded-xl border border-line/70 bg-[#f8faf9] p-4">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-ink/75">Reference</span>
                <span className="font-mono text-xs text-ink/55">{reference.slice(0, 12)}...</span>
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-center text-sm font-medium text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading || !reference || !token}
              className="button w-full"
            >
              {loading ? "Processing..." : "Complete Demo Payment"}
            </button>

            <p className="text-center text-xs text-ink/50">
              Demo mode is for testing only. Enable it by setting <code className="bg-[#f8faf9] px-1 rounded">DEMO_MODE=true</code> in your backend <code className="bg-[#f8faf9] px-1 rounded">.env</code> file.
            </p>
          </form>
        )}
      </section>
    </main>
  );
}

export default function DemoPaymentPage() {
  return (
    <Suspense fallback={null}>
      <DemoPaymentContent />
    </Suspense>
  );
}
