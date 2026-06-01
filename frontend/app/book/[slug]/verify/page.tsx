"use client";

import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

export default function VerifyPage({ params, searchParams }: { params: { slug: string }; searchParams: { booking_id?: string; token?: string } }) {
  const [message, setMessage] = useState("Checking payment...");
  const [manageUrl, setManageUrl] = useState("");

  useEffect(() => {
    if (!searchParams.booking_id) {
      setMessage("Payment pending");
      return;
    }
    let attempts = 0;
    const timer = window.setInterval(async () => {
      attempts += 1;
      const status = await api.bookingStatus(params.slug, searchParams.booking_id!, searchParams.token);
      if (status.manage_url) setManageUrl(status.manage_url);
      if (status.booking_status === "confirmed") {
        setMessage("Booking confirmed");
        window.clearInterval(timer);
      }
      if (attempts >= 20) {
        setMessage("Payment pending");
        window.clearInterval(timer);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [params.slug, searchParams.booking_id, searchParams.token]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <section className="panel grid w-full gap-3 text-center">
        <p className="eyebrow mx-auto">Payment status</p>
        <h1 className="text-3xl font-semibold">{message}</h1>
        <p className="muted">This page updates automatically after Paystack confirms the transaction.</p>
        {manageUrl && (
          <a className="button" href={manageUrl}>
            Manage booking
          </a>
        )}
      </section>
    </main>
  );
}
