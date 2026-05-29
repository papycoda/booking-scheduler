import "./globals.css";

export const metadata = {
  title: "Booking Scheduler",
  description: "Multi-tenant appointment booking for small businesses",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
