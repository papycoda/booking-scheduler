"use client";

import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

export default function VerifyPage({ params, searchParams }: { params: { slug: string }; searchParams: { booking_id?: string; token?: string } }) {
  const [message, setMessage] = useState("Checking payment");
  const [state, setState] = useState<"checking" | "confirmed" | "pending">("checking");
  const [manageUrl, setManageUrl] = useState("");

  useEffect(() => {
    if (!searchParams.booking_id) {
      setMessage("Payment pending");
      setState("pending");
      return;
    }
    let attempts = 0;
    const timer = window.setInterval(async () => {
      attempts += 1;
      const status = await api.bookingStatus(params.slug, searchParams.booking_id!, searchParams.token);
      if (status.manage_url) setManageUrl(status.manage_url);
      if (status.booking_status === "confirmed") {
        setMessage("Booking confirmed");
        setState("confirmed");
        window.clearInterval(timer);
      }
      if (attempts >= 20) {
        setMessage("Payment pending");
        setState("pending");
        window.clearInterval(timer);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [params.slug, searchParams.booking_id, searchParams.token]);

  return (
    <main className="grid min-h-screen place-items-center bg-gradient-to-br from-[#c8d6cd] via-[#f3f6f4] to-[#dde5e0] px-5 py-10 text-ink">
      <section className="public-glass grid w-full max-w-md justify-items-center gap-5 p-8 text-center">
        <div className="grid h-20 w-20 place-items-center rounded-full bg-white shadow-sm">
          {state === "confirmed" ? (
            <svg className="h-10 w-10 text-action" fill="none" stroke="currentColor" strokeWidth="2.4" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          ) : (
            <span className="h-10 w-10 animate-spin rounded-full border-4 border-[#caa26b]/25 border-t-[#caa26b]" />
          )}
        </div>
        <div>
          <p className="eyebrow mx-auto">Payment status</p>
          <h1 className="mt-2 text-3xl font-bold tracking-normal">{message}</h1>
          <p className="mt-3 text-sm font-medium leading-relaxed text-ink/65">
            {state === "confirmed" ? "Your booking is confirmed. Keep your manage link so you can request changes if needed." : "This page updates automatically after checkout confirms the transaction."}
          </p>
        </div>
        {manageUrl && (
          <a className="button w-full" href={manageUrl}>
            Manage booking
          </a>
        )}
      </section>
    </main>
  );
}
