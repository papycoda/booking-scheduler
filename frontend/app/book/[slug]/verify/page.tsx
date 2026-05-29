"use client";

import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

export default function VerifyPage({ params, searchParams }: { params: { slug: string }; searchParams: { booking_id?: string } }) {
  const [message, setMessage] = useState("Checking payment...");

  useEffect(() => {
    if (!searchParams.booking_id) {
      setMessage("Payment pending");
      return;
    }
    let attempts = 0;
    const timer = window.setInterval(async () => {
      attempts += 1;
      const status = await api.bookingStatus(params.slug, searchParams.booking_id!);
      if ((status as { booking_status?: string }).booking_status === "confirmed") {
        setMessage("Booking confirmed");
        window.clearInterval(timer);
      }
      if (attempts >= 20) {
        setMessage("Payment pending");
        window.clearInterval(timer);
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [params.slug, searchParams.booking_id]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-5">
      <h1 className="text-3xl font-semibold">{message}</h1>
    </main>
  );
}
