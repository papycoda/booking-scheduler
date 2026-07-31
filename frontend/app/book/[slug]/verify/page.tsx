"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "../../../../lib/api";

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyStatus />
    </Suspense>
  );
}

function VerifyStatus() {
  const router = useRouter();
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const slug = params.slug ?? "";
  const bookingId = searchParams.get("booking_id") ?? "";
  const token = searchParams.get("token") ?? undefined;
  const [message, setMessage] = useState("Confirming payment...");

  useEffect(() => {
    if (!slug || !bookingId) {
      setMessage("Booking link is missing details.");
      return;
    }
    let attempts = 0;
    let cancelled = false;
    let timer: number | undefined;

    async function checkPaymentStatus() {
      try {
        attempts += 1;
        const status = await api.bookingStatus(slug, bookingId, token);
        if (cancelled) return;
        if (status.booking_status === "confirmed" && status.manage_url) {
          router.replace(status.manage_url);
          return;
        }
        if (attempts >= 20) {
          setMessage("Payment is still processing. Refresh this page in a moment.");
          if (timer) window.clearInterval(timer);
        }
      } catch {
        if (!cancelled) setMessage("Could not confirm payment yet. Refresh this page in a moment.");
        if (timer) window.clearInterval(timer);
      }
    }

    void checkPaymentStatus();
    timer = window.setInterval(() => void checkPaymentStatus(), 3000);
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [bookingId, router, slug, token]);

  return (
    <main className="grid min-h-screen place-items-center bg-[#f5f8f6] px-5 py-10 text-ink">
      <p className="text-sm font-semibold text-ink/65">{message}</p>
    </main>
  );
}
