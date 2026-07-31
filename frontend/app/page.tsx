import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  CalendarBlank,
  Check,
  CheckCircle,
  Clock,
  CreditCard,
  LinkSimple,
  Robot,
  ShieldCheck,
  Sparkle,
  Storefront,
  UserCircle,
} from "@phosphor-icons/react/ssr";

const steps = [
  {
    icon: Storefront,
    number: "01",
    title: "Set up what people can book",
    description: "Add your services, sessions, spaces or experiences, then set the price, duration and availability.",
  },
  {
    icon: LinkSimple,
    number: "02",
    title: "Share one simple link",
    description: "Send your Bookie link on WhatsApp, Instagram, your bio, or anywhere clients find you.",
  },
  {
    icon: CreditCard,
    number: "03",
    title: "Get booked and paid",
    description: "Clients choose an available time and pay the required deposit to secure the booking.",
  },
];

const features = [
  {
    icon: CalendarBlank,
    title: "Live availability",
    description: "Clients only see times that are actually open, helping you avoid double bookings.",
  },
  {
    icon: CreditCard,
    title: "Deposit collection",
    description: "Collect secure Paystack deposits before a booking is confirmed.",
  },
  {
    icon: UserCircle,
    title: "No customer account",
    description: "Clients can book and pay without creating an account or downloading an app.",
  },
  {
    icon: Clock,
    title: "One organised dashboard",
    description: "Manage bookings, availability, services, staff, and payment status in one place.",
  },
];

const times = ["9:00", "10:00", "11:00", "12:00", "1:00", "2:00"];

function Wordmark({ light = false }: { light?: boolean }) {
  return (
    <span className={`text-[1.65rem] font-black tracking-[-0.055em] ${light ? "text-white" : "text-[#092d20]"}`}>
      Bookie
    </span>
  );
}

function BookingPhone() {
  return (
    <div className="relative z-20 mx-auto w-[248px] rounded-[2.4rem] border-[7px] border-[#173a2d] bg-white p-2 shadow-[0_28px_70px_rgba(5,45,31,0.22)] sm:w-[270px]">
      <div className="mx-auto mb-2 h-4 w-20 rounded-b-xl bg-[#173a2d]" />
      <div className="overflow-hidden rounded-[1.7rem] border border-[#e1e9e4] bg-white">
        <div className="relative h-24">
          <Image src="/landing/studio-interior.png" alt="Warm modern beauty studio" fill className="object-cover" sizes="270px" priority />
          <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2 py-1 text-[9px] font-bold text-[#0e4731] shadow-sm">Glow Studios</span>
        </div>
        <div className="space-y-3 p-3 text-[#0f2119]">
          <div>
            <p className="text-[10px] font-bold">1. Choose a service</p>
            <div className="mt-1 flex items-center justify-between rounded-lg border border-[#dce6e0] px-2 py-2 text-[9px] font-semibold">
              <span>Makeup · Full glam</span><span>₦30,000</span>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-bold">2. Select a date</p>
            <div className="mt-1 flex items-center justify-between rounded-lg border border-[#dce6e0] px-2 py-2 text-[9px]">
              <span>Saturday, 24 May</span><CalendarBlank size={13} />
            </div>
          </div>
          <div>
            <p className="text-[10px] font-bold">3. Choose a time</p>
            <div className="mt-1 grid grid-cols-3 gap-1">
              {times.map((time) => (
                <span key={time} className={`rounded-md border px-1 py-1.5 text-center text-[8px] font-semibold ${time === "12:00" ? "border-[#0f6b4f] bg-[#0f6b4f] text-white" : "border-[#dce6e0]"}`}>{time}</span>
              ))}
            </div>
          </div>
          <div className="rounded-lg bg-[#f3f7f4] p-2">
            <p className="text-[8px] font-semibold text-[#60766a]">Deposit due now</p>
            <strong className="text-sm">₦10,000</strong>
          </div>
          <div className="flex items-center justify-center gap-1 rounded-lg bg-[#0f6b4f] py-2 text-[9px] font-bold text-white">
            Pay ₦10,000 deposit <ArrowRight size={11} weight="bold" />
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardPreview() {
  const schedule = [
    ["10:00", "Tunde Adeyemi", "Haircut"],
    ["13:00", "Amaka Okafor", "Makeup · Full glam"],
    ["15:00", "Bola Johnson", "Consultation"],
  ];
  return (
    <div className="absolute right-0 top-14 hidden w-[390px] overflow-hidden rounded-[1.6rem] border border-white bg-white shadow-[0_30px_75px_rgba(5,45,31,0.17)] md:grid md:grid-cols-[92px_1fr] lg:w-[430px]">
      <aside className="bg-[#0a4d37] p-4 text-white">
        <span className="text-base font-black tracking-[-0.04em]">Bookie</span>
        <div className="mt-8 grid gap-4 text-[8px] font-semibold text-white/65">
          <span className="rounded-lg bg-white/12 px-2 py-2 text-white">Dashboard</span>
          <span>Bookings</span><span>Services</span><span>Availability</span><span>Payments</span>
        </div>
      </aside>
      <div className="p-5">
        <p className="text-sm font-bold">Dashboard</p>
        <div className="mt-4 rounded-xl border border-[#e5ebe7] p-3">
          <p className="text-[9px] font-bold text-[#60766a]">UPCOMING BOOKING</p>
          <div className="mt-3 flex items-center gap-2">
            <Image src="/landing/customer-avatar.png" alt="Customer avatar" width={34} height={34} className="h-9 w-9 rounded-full object-cover" />
            <div className="min-w-0 flex-1"><p className="truncate text-[10px] font-bold">Amaka Okafor</p><p className="text-[8px] text-[#60766a]">Makeup · Full glam</p></div>
            <span className="rounded-full bg-[#e8f4ec] px-2 py-1 text-[7px] font-bold text-[#0f6b4f]">Confirmed</span>
          </div>
          <div className="mt-3 flex justify-between border-t border-[#eef2ef] pt-3 text-[9px]">
            <span>Sat, 24 May · 13:00</span><strong>₦10,000 paid</strong>
          </div>
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between"><p className="text-[10px] font-bold">Today&apos;s schedule</p><span className="text-[8px] text-[#60766a]">View all</span></div>
          <div className="mt-2 divide-y divide-[#eef2ef] rounded-xl border border-[#e5ebe7] px-3">
            {schedule.map(([time, name, service]) => (
              <div key={time} className="grid grid-cols-[38px_1fr_auto] items-center gap-2 py-2.5 text-[8px]">
                <strong>{time}</strong><span><b className="block">{name}</b><span className="text-[#60766a]">{service}</span></span><CheckCircle size={14} weight="fill" className="text-[#0f6b4f]" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function CustomerJourney() {
  const cards = [
    { label: "Choose service", body: <><div className="relative h-20 overflow-hidden rounded-lg"><Image src="/landing/studio-interior.png" alt="Glow Studios interior" fill className="object-cover" sizes="180px" /></div><strong className="mt-2 block text-xs">Glow Studios</strong><span className="text-[10px] text-[#60766a]">Makeup appointment</span></> },
    { label: "Pick date & time", body: <><p className="text-[10px] font-bold">May 2026</p><div className="mt-3 grid grid-cols-5 gap-1 text-center text-[9px]">{[18,19,20,21,22,23,24,25,26,27].map(day => <span key={day} className={`rounded-md py-1 ${day === 24 ? "bg-[#0f6b4f] text-white" : "bg-[#f4f7f5]"}`}>{day}</span>)}</div></> },
    { label: "Pay deposit", body: <><p className="text-[10px] text-[#60766a]">Deposit due now</p><strong className="mt-1 block text-xl">₦10,000</strong><div className="mt-4 rounded-lg bg-[#0f6b4f] py-2 text-center text-[9px] font-bold text-white">Pay securely</div></> },
    { label: "Confirmed", body: <><CheckCircle size={42} weight="fill" className="mx-auto text-[#0f6b4f]" /><strong className="mt-3 block text-center text-xs">Booking confirmed!</strong><p className="mt-1 text-center text-[9px] text-[#60766a]">You&apos;ll receive a confirmation shortly.</p></> },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => (
        <div key={card.label}>
          <div className="mb-3 flex items-center gap-2 text-[10px] font-bold text-[#0e4731]"><span className="grid h-6 w-6 place-items-center rounded-full bg-[#0f6b4f] text-white">{index + 1}</span>{card.label}</div>
          <div className="min-h-44 rounded-2xl border border-[#e1e9e4] bg-white p-3 shadow-[0_15px_35px_rgba(5,45,31,0.06)]">{card.body}</div>
        </div>
      ))}
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#fffdf9] font-sans text-[#0b2c20]">
      <header className="border-b border-[#e9eee9] bg-[#fffdf9]/95">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" aria-label="Bookie home"><Wordmark /></Link>
          <nav className="hidden items-center gap-8 text-sm font-semibold text-[#40594e] md:flex" aria-label="Main navigation">
            <a href="#how-it-works" className="transition hover:text-[#0f6b4f]">How it works</a>
            <a href="#features" className="transition hover:text-[#0f6b4f]">Features</a>
            <a href="#ai-front-desk" className="transition hover:text-[#0f6b4f]">AI front desk</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden rounded-xl px-3 py-2 text-sm font-bold text-[#0b2c20] hover:bg-[#f2f6f2] sm:inline-flex">Sign in</Link>
            <Link href="/register" className="inline-flex min-h-11 items-center rounded-xl bg-[#0f6b4f] px-4 text-sm font-bold text-white shadow-[0_12px_24px_rgba(15,107,79,0.18)] transition hover:-translate-y-0.5 hover:bg-[#0a563f]">Create your booking page</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto grid min-h-[680px] max-w-7xl items-center gap-14 px-5 py-16 sm:px-8 lg:grid-cols-[0.88fr_1.12fr] lg:py-20">
        <div className="relative z-30 max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#dbe7df] bg-white px-3 py-1.5 text-xs font-bold text-[#0f6b4f]"><ShieldCheck size={15} weight="fill" /> Booking made simple</span>
          <h1 className="mt-6 text-[clamp(3rem,6vw,5.6rem)] font-black leading-[0.95] tracking-[-0.065em] text-[#092d20]">
            Your bookings, availability and deposits—handled through one simple link.
          </h1>
          <p className="mt-7 max-w-xl text-lg font-medium leading-8 text-[#50685d]">Set up what people can book, share your link, and let them choose a time and pay without the back-and-forth.</p>
          <div className="mt-9 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
            <Link href="/register" className="group inline-flex min-h-14 w-full items-center justify-between rounded-2xl bg-[#0f6b4f] px-5 text-sm font-bold text-white shadow-[0_16px_32px_rgba(15,107,79,0.2)] transition hover:-translate-y-0.5 hover:bg-[#0a563f] sm:w-auto sm:min-w-[250px]">
              <span>Create your booking page</span><span className="grid h-8 w-8 place-items-center rounded-full bg-white/15 transition group-hover:translate-x-0.5"><ArrowRight size={17} weight="bold" /></span>
            </Link>
            <Link href="/book/bookie-live-demo" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold text-[#0f6b4f] transition hover:bg-[#f1f7f3] sm:border sm:border-[#bcd2c5] sm:bg-white">See a live booking page <ArrowRight size={15} weight="bold" /></Link>
          </div>
          <p className="mt-5 flex items-center gap-2 text-sm font-semibold text-[#60766a]"><Check size={16} weight="bold" className="text-[#0f6b4f]" /> People can book without an app or account</p>
        </div>
        <div className="relative min-h-[570px] rounded-[2.5rem] bg-[#eef4ef] p-8 sm:p-12">
          <div className="absolute inset-x-8 top-8 flex items-center justify-between text-xs font-bold text-[#60766a]"><span>BOOKING EXPERIENCE</span><span className="rounded-full bg-[#ffdfcc] px-3 py-1 text-[#8a4721]">Live product</span></div>
          <div className="relative mt-12 flex h-[490px] items-center justify-start md:pl-2 lg:pl-5">
            <BookingPhone />
            <DashboardPreview />
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-[#f2dfd2] bg-[#fff5ed] px-6 py-5 text-center text-sm font-bold text-[#173a2d] sm:flex-row sm:gap-5">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-[#ffdcc7] text-[#80441f]"><Storefront size={21} weight="duotone" /></span>
          For anyone offering something people can book—time, services, spaces, sessions or experiences.
        </div>
      </div>

      <section id="how-it-works" className="mx-auto max-w-7xl scroll-mt-20 px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[#0f6b4f]">Simple by design</p>
          <h2 className="mt-3 text-4xl font-black tracking-[-0.045em] sm:text-5xl">From enquiry to confirmed booking</h2>
        </div>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {steps.map(({ icon: Icon, number, title, description }) => (
            <article key={number} className="relative rounded-3xl border border-[#e3eae5] bg-white p-7 shadow-[0_22px_55px_rgba(5,45,31,0.045)]">
              <div className="flex items-center justify-between"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#ffdfcc] text-[#7c421f]"><Icon size={24} weight="duotone" /></span><span className="text-sm font-black text-[#b9c7bf]">{number}</span></div>
              <h3 className="mt-7 text-xl font-black tracking-[-0.025em]">{title}</h3>
              <p className="mt-3 text-sm font-medium leading-6 text-[#60766a]">{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="features" className="scroll-mt-20 bg-[#f4f8f4] py-24">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="max-w-2xl"><p className="text-xs font-black uppercase tracking-[0.18em] text-[#0f6b4f]">Everything in one place</p><h2 className="mt-3 text-4xl font-black tracking-[-0.045em] sm:text-5xl">Run your bookings without the chaos.</h2></div>
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, description }) => (
              <article key={title} className="rounded-3xl border border-[#dfe8e1] bg-white p-6">
                <span className="grid h-12 w-12 place-items-center rounded-full bg-[#e8f2e9] text-[#0f6b4f]"><Icon size={24} weight="duotone" /></span>
                <h3 className="mt-6 text-lg font-black tracking-[-0.02em]">{title}</h3><p className="mt-3 text-sm font-medium leading-6 text-[#60766a]">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="ai-front-desk" className="mx-auto max-w-7xl scroll-mt-20 px-5 py-24 sm:px-8">
        <div className="overflow-hidden rounded-[2rem] bg-[#082f22] text-white">
          <div className="grid gap-10 px-7 py-10 sm:px-12 sm:py-14 lg:grid-cols-[0.9fr_1.1fr] lg:px-16 lg:py-16">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-[#ffdfcc] px-3 py-1.5 text-xs font-black uppercase tracking-[0.12em] text-[#7b401d]"><Sparkle size={14} weight="fill" /> Coming soon</span>
              <h2 className="mt-6 text-4xl font-black leading-tight tracking-[-0.045em] sm:text-5xl">An AI front desk that knows when to call you in.</h2>
              <p className="mt-5 max-w-xl text-base font-medium leading-7 text-white/70">Bookie will handle routine enquiries, check real availability, guide clients into the booking flow, and hand unusual requests to you with the context attached.</p>
            </div>
            <div className="grid gap-3 self-center">
              {["Answer common questions through messaging channels", "Use your real services, staff and availability", "Prepare bookings without bypassing confirmation", "Pause immediately when a human takes over"].map((item) => (
                <div key={item} className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.06] px-5 py-4 text-sm font-bold"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#0f6b4f]"><Check size={17} weight="bold" /></span>{item}</div>
              ))}
              <div className="mt-2 flex items-center gap-3 text-sm font-semibold text-[#b9d6c8]"><Robot size={23} weight="duotone" /> Being built carefully, with human handoff and booking safeguards from day one.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-24 sm:px-8">
        <div className="rounded-[2rem] border border-[#e1e9e4] bg-[#f6faf6] p-6 sm:p-10 lg:p-12">
          <div className="mb-10 flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><p className="text-xs font-black uppercase tracking-[0.18em] text-[#0f6b4f]">The customer experience</p><h2 className="mt-3 text-4xl font-black tracking-[-0.045em]">Four clear steps. No back-and-forth.</h2></div><Link href="/book/bookie-live-demo" className="inline-flex min-h-11 items-center justify-center rounded-xl border border-[#0f6b4f] bg-white px-5 text-sm font-bold text-[#0f6b4f] hover:bg-[#eef6f1]">Try the live booking page</Link></div>
          <CustomerJourney />
        </div>
      </section>

      <section className="bg-[#0a4d37] px-5 py-20 text-white sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-8 lg:flex-row lg:items-center">
          <div><h2 className="max-w-2xl text-4xl font-black tracking-[-0.045em] sm:text-5xl">Spend less time arranging appointments.</h2><p className="mt-4 text-base font-medium text-white/70">Create your booking page in minutes and start accepting bookings and deposits.</p></div>
          <Link href="/register" className="inline-flex min-h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-7 text-sm font-black text-[#0a4d37] shadow-[0_18px_35px_rgba(0,0,0,0.16)] transition hover:-translate-y-0.5">Create your booking page <ArrowRight size={17} weight="bold" /></Link>
        </div>
      </section>

      <footer className="bg-[#07281d] px-5 py-10 text-white sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-7 sm:flex-row sm:items-center sm:justify-between"><Wordmark light /><div className="flex flex-wrap gap-6 text-sm font-semibold text-white/65"><a href="#how-it-works" className="hover:text-white">How it works</a><a href="#features" className="hover:text-white">Features</a><a href="#ai-front-desk" className="hover:text-white">AI front desk</a><Link href="/login" className="hover:text-white">Sign in</Link></div><span className="text-xs font-semibold text-white/45">© 2026 Bookie</span></div>
      </footer>
    </main>
  );
}
