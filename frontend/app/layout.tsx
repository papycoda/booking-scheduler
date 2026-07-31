import "./globals.css";

export const metadata = {
  title: "Bookie — Bookings and deposits through one simple link",
  description: "Create a booking page, share your link, and let clients choose a time and pay their deposit without the back-and-forth.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning={true}>{children}</body>
    </html>
  );
}
