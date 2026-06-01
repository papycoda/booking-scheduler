import Link from "next/link";

type AuthShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  switchHref: string;
  switchLabel: string;
  formTitle: string;
  formSubtitle: string;
  children: React.ReactNode;
};

function PlantLeft() {
  return (
    <svg viewBox="0 0 200 300" fill="none" className="h-full w-full" aria-hidden="true">
      <path d="M10 300 C 30 220, 55 150, 95 80" stroke="#6f8b7a" strokeWidth="1" strokeLinecap="round" />
      <path d="M45 210 Q 15 190, 8 160 Q 22 140, 52 175 Z" fill="#d9ebe1" fillOpacity="0.72" stroke="#6f8b7a" strokeWidth="0.8" />
      <circle cx="8" cy="160" r="2.5" fill="#caa26b" />
      <path d="M60 170 Q 35 140, 42 110 Q 62 110, 70 142 Z" fill="#d9ebe1" fillOpacity="0.72" stroke="#6f8b7a" strokeWidth="0.8" />
      <path d="M78 130 Q 105 110, 115 80 Q 95 70, 85 105 Z" fill="#d9ebe1" fillOpacity="0.72" stroke="#6f8b7a" strokeWidth="0.8" />
      <path d="M35 245 Q 10 235, 2 210 Q 15 190, 42 215 Z" fill="#d9ebe1" fillOpacity="0.72" stroke="#6f8b7a" strokeWidth="0.8" />
      <circle cx="2" cy="210" r="2.5" fill="#caa26b" />
      <circle cx="95" cy="220" r="3.5" fill="#6f8b7a" />
      <circle cx="78" cy="250" r="2.5" fill="#6f8b7a" />
      <line x1="35" y1="245" x2="15" y2="265" stroke="#6f8b7a" strokeWidth="0.8" strokeDasharray="2 2" />
    </svg>
  );
}

function PlantTop() {
  return (
    <svg viewBox="0 0 200 200" fill="none" className="h-full w-full" aria-hidden="true">
      <path d="M110 0 C 100 60, 80 100, 40 140" stroke="#6f8b7a" strokeWidth="1" />
      <path d="M102 35 Q 75 25, 68 5 Q 88 5, 98 25 Z" fill="#d9ebe1" fillOpacity="0.65" stroke="#6f8b7a" strokeWidth="0.8" />
      <path d="M90 65 Q 60 65, 52 45 Q 72 35, 85 55 Z" fill="#d9ebe1" fillOpacity="0.65" stroke="#6f8b7a" strokeWidth="0.8" />
      <circle cx="52" cy="45" r="2" fill="#caa26b" />
    </svg>
  );
}

function PlantRight() {
  return (
    <svg viewBox="0 0 150 250" fill="none" className="h-full w-full" aria-hidden="true">
      <path d="M150 200 C 110 160, 90 110, 75 40" stroke="#6f8b7a" strokeWidth="1" />
      <path d="M115 155 Q 85 165, 78 185 Q 93 200, 113 170 Z" fill="#d9ebe1" fillOpacity="0.65" stroke="#6f8b7a" strokeWidth="0.8" />
      <circle cx="78" cy="185" r="2.5" fill="#caa26b" />
      <path d="M95 115 Q 65 120, 60 140 Q 80 150, 93 127 Z" fill="#d9ebe1" fillOpacity="0.65" stroke="#6f8b7a" strokeWidth="0.8" />
    </svg>
  );
}

function CalendarIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.22 21h13.56A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.22 9h13.56A2.25 2.25 0 0121 11.25v7.5" />
    </svg>
  );
}

function FeatureIcon({ type }: { type: "clock" | "money" | "image" }) {
  if (type === "clock") {
    return (
      <svg className="h-5 w-5 text-[#3d5245]" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
  }
  if (type === "money") {
    return (
      <svg className="h-5 w-5 text-[#3d5245]" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.854-1.106-2.24 0-3.094l.018-.015c1.171-.879 3.07-.879 4.242 0 .586.44.977 1.054 1.172 1.74M3 5.25h18M3 18.75h18" />
      </svg>
    );
  }
  return (
    <svg className="h-5 w-5 text-[#3d5245]" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 19.5h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5z" />
    </svg>
  );
}

export function AuthShell({
  eyebrow,
  title,
  description,
  switchHref,
  switchLabel,
  formTitle,
  formSubtitle,
  children,
}: AuthShellProps) {
  return (
    <main className="relative isolate flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-[#e6eee9] via-[#dde8e2] to-[#d2e0d7] p-4 text-[#112219] md:p-12">
      <div className="pointer-events-none absolute bottom-0 left-0 z-0 h-[450px] w-80 opacity-70">
        <PlantLeft />
      </div>
      <div className="pointer-events-none absolute left-1/3 top-0 z-0 h-72 w-72 opacity-60">
        <PlantTop />
      </div>
      <div className="pointer-events-none absolute right-0 top-1/4 z-0 h-96 w-56 opacity-60">
        <PlantRight />
      </div>
      <svg className="pointer-events-none absolute bottom-10 right-14 z-0 h-10 w-10 text-white/70" fill="currentColor" viewBox="0 0 100 100" aria-hidden="true">
        <path d="M50 0 C52 38, 62 48, 100 50 C62 52, 52 62, 50 100 C48 62, 38 52, 0 50 C38 48, 48 38, 50 0 Z" />
      </svg>

      <section className="relative z-10 grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-4 lg:grid-cols-12">
        <aside className="relative z-10 space-y-7 text-[#112219] lg:col-span-6">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/60 bg-white/25 text-[#2d4236] shadow-sm backdrop-blur-sm">
            <CalendarIcon />
          </div>

          <div className="space-y-4">
            <span className="block text-[10px] font-bold uppercase tracking-[0.2em] text-[#3d5245]">{eyebrow}</span>
            <h1 className="max-w-[560px] font-serif text-4xl font-normal leading-[1.12] tracking-normal text-[#112219] sm:text-5xl lg:text-[54px]">
              {title}
            </h1>
            <p className="max-w-lg text-[13px] font-medium leading-relaxed text-[#33473b]">{description}</p>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-2">
            {[
              { type: "clock" as const, title: "24/7", desc: "Public booking link" },
              { type: "money" as const, title: "NGN", desc: "Deposit collection" },
              { type: "image" as const, title: "Inspo", desc: "Image uploads" },
            ].map((feature) => (
              <div key={feature.title} className="flex h-[105px] flex-col justify-between rounded-xl border border-white/45 bg-[#edf2ee]/60 p-4 shadow-sm backdrop-blur-sm">
                <FeatureIcon type={feature.type} />
                <div>
                  <p className="text-base font-bold leading-none text-[#112219]">{feature.title}</p>
                  <p className="mt-1 text-[10px] font-medium text-[#485c50]">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <section className="relative z-20 mx-auto w-full max-w-lg pointer-events-auto lg:col-span-6 lg:ml-auto">
          <div className="relative z-20 rounded-2xl border border-white/70 bg-[#f8fbf9]/75 p-7 shadow-[0_40px_80px_rgba(17,34,25,0.06)] backdrop-blur-md sm:p-9">
            <div className="mb-7 flex items-start justify-between gap-4">
              <div>
                <span className="mb-0.5 block text-[10px] font-bold uppercase tracking-widest text-[#3d5245]">Start booking</span>
                <h2 className="text-2xl font-bold tracking-normal text-[#112219]">{formTitle}</h2>
                <p className="mt-0.5 text-xs font-medium text-[#485c50]">{formSubtitle}</p>
              </div>
              <Link href={switchHref} className="rounded-lg border border-white/60 bg-white/45 px-3.5 py-1.5 text-xs font-semibold text-[#112219] shadow-sm transition hover:bg-white/65">
                {switchLabel}
              </Link>
            </div>
            <div className="auth-form">{children}</div>
          </div>
        </section>
      </section>
    </main>
  );
}
