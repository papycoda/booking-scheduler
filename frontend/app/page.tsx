import Image from "next/image";
import Link from "next/link";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import {
  ArrowRight,
  BellRinging,
  CalendarBlank,
  CalendarCheck,
  Check,
  CheckCircle,
  Clock,
  CreditCard,
  LinkSimple,
  Robot,
  ShieldCheck,
  Sparkle,
  SquaresFour,
  Storefront,
  UserCircle,
  UsersThree,
} from "@phosphor-icons/react/ssr";

const bodyFont = DM_Sans({ subsets: ["latin"], display: "swap" });
const displayFont = DM_Serif_Display({ subsets: ["latin"], weight: "400", display: "swap" });

const steps = [
  {
    icon: Storefront,
    number: "1",
    title: "Set up what people can book",
    description: "Add services, sessions, spaces or experiences, then set the price, duration and availability.",
  },
  {
    icon: LinkSimple,
    number: "2",
    title: "Share your Bookie link",
    description: "Send it on WhatsApp, Instagram, your website or anywhere people already find you.",
  },
  {
    icon: CalendarCheck,
    number: "3",
    title: "Get booked and paid",
    description: "Clients choose a real available time and pay the required deposit to confirm their booking.",
  },
];

const featureCards = [
  {
    icon: CalendarBlank,
    title: "Availability that stays accurate",
    description: "Only show times that are actually open and protect your schedule from double bookings.",
  },
  {
    icon: CreditCard,
    title: "Deposits before confirmation",
    description: "Use Paystack to collect the amount you require before a booking is secured.",
  },
  {
    icon: BellRinging,
    title: "Automatic reminders",
    description: "Help clients remember upcoming appointments with scheduled email and messaging reminders.",
    badge: "Available now",
  },
  {
    icon: UsersThree,
    title: "No customer account required",
    description: "People can book and pay without downloading an app or creating another password.",
  },
];

const schedule = [
  { time: "10:00", name: "Ada Nwosu", service: "Strategy session", status: "Confirmed" },
  { time: "13:30", name: "Moyo Daniels", service: "Studio booking", status: "Deposit paid" },
  { time: "16:00", name: "Kemi Adebayo", service: "Consultation", status: "Confirmed" },
];

function Wordmark({ light = false }: { light?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 text-xl font-black tracking-[-0.04em] ${light ? "text-white" : "text-[#092d20]"}`}>
      <span className={`grid h-8 w-8 place-items-center rounded-lg text-sm ${light ? "bg-white text-[#0a4d37]" : "bg-[#0a4d37] text-white"}`}>B</span>
      Bookie
    </span>
  );
}

function DashboardPreview({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`overflow-hidden rounded-[1.4rem] border border-[#dfe7e1] bg-white shadow-[0_28px_70px_rgba(35,58,44,0.13)] ${compact ? "text-[10px]" : ""}`}>
      <div className="flex items-center justify-between border-b border-[#e8eee9] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-[#0a4d37] text-[10px] font-black text-white">B</span>
          <strong className="text-xs">Dashboard</strong>
        </div>
        <span className="rounded-full bg-[#e9f4ed] px-2 py-1 text-[8px] font-bold text-[#0f6b4f]">Today</span>
      </div>
      <div className="grid grid-cols-[88px_1fr] sm:grid-cols-[112px_1fr]">
        <aside className="border-r border-[#edf1ee] bg-[#fbfcfb] p-3">
          <div className="grid gap-2 text-[8px] font-semibold text-[#64776d] sm:text-[9px]">
            {["Overview", "Bookings", "Services", "Staff", "Availability"].map((item, index) => (
              <span key={item} className={`rounded-lg px-2 py-2 ${index === 0 ? "bg-[#e8f3ec] font-bold text-[#0f6b4f]" : ""}`}>{item}</span>
            ))}
          </div>
        </aside>
        <div className="min-w-0 p-3 sm:p-4">
          <div className="grid grid-cols-3 gap-2">
            {[["Bookings", "8"], ["Deposits", "₦85k"], ["Open slots", "12"]].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-[#e5ebe7] bg-[#fbfcfb] p-2.5">
                <p className="text-[7px] font-semibold text-[#718178] sm:text-[8px]">{label}</p>
                <strong className="mt-1 block text-xs sm:text-sm">{value}</strong>
              </div>
            ))}
          </div>
          <div className="mt-3 rounded-xl border border-[#e5ebe7] bg-white p-3">
            <div className="flex items-center justify-between">
              <strong className="text-[9px] sm:text-[10px]">Today&apos;s schedule</strong>
              <span className="text-[7px] font-semibold text-[#0f6b4f] sm:text-[8px]">View bookings</span>
            </div>
            <div className="mt-2 divide-y divide-[#eef2ef]">
              {schedule.map((booking) => (
                <div key={booking.time} className="grid grid-cols-[34px_1fr_auto] items-center gap-2 py-2 text-[7px] sm:grid-cols-[42px_1fr_auto] sm:text-[8px]">
                  <strong>{booking.time}</strong>
                  <span className="min-w-0"><b className="block truncate">{booking.name}</b><span className="block truncate text-[#708077]">{booking.service}</span></span>
                  <span className="hidden rounded-full bg-[#edf6f0] px-2 py-1 font-bold text-[#0f6b4f] sm:inline">{booking.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function BookingPreview() {
  const times = ["9:00 AM", "10:30 AM", "12:00 PM", "2:00 PM"];
  return (
    <div className="w-full max-w-[280px] overflow-hidden rounded-[1.6rem] border border-[#dfe7e1] bg-white shadow-[0_26px_65px_rgba(22,56,41,0.2)]">
      <div className="relative h-24">
        <Image src="/landing/studio-interior.png" alt="A bright modern bookable studio" fill className="object-cover" sizes="280px" priority />
        <div className="absolute inset-x-3 bottom-3 flex items-end justify-between text-white">
          <div><p className="text-[8px] font-bold uppercase tracking-[0.12em] text-white/80">Your booking page</p><strong className="text-sm">Northstar Studio</strong></div>
          <span className="rounded-full bg-white/90 px-2 py-1 text-[7px] font-bold text-[#0a4d37]">Open today</span>
        </div>
      </div>
      <div className="space-y-3 p-3.5">
        <div>
          <p className="text-[9px] font-black text-[#17382b]">1. Choose what to book</p>
          <div className="mt-1.5 flex items-center justify-between rounded-lg border border-[#dce6e0] px-2.5 py-2 text-[8px] font-semibold"><span>Creative studio · 90 min</span><span>₦25,000</span></div>
        </div>
        <div>
          <p className="text-[9px] font-black text-[#17382b]">2. Pick an available time</p>
          <div className="mt-1.5 grid grid-cols-2 gap-1.5">
            {times.map((time) => <span key={time} className={`rounded-md border px-2 py-1.5 text-center text-[7px] font-bold ${time === "12:00 PM" ? "border-[#0f6b4f] bg-[#0f6b4f] text-white" : "border-[#dce6e0] text-[#40594e]"}`}>{time}</span>)}
          </div>
        </div>
        <div className="flex items-center justify-between rounded-lg bg-[#f1f6f2] p-2.5"><span className="text-[8px] font-semibold text-[#60766a]">Deposit due now</span><strong className="text-sm">₦10,000</strong></div>
        <div className="flex items-center justify-center gap-1.5 rounded-lg bg-[#0f6b4f] py-2.5 text-[8px] font-black text-white">Continue to payment <ArrowRight size={11} weight="bold" /></div>
      </div>
    </div>
  );
}

function ProductShowcase() {
  return (
    <div className="relative rounded-[2rem] border border-[#eddfc1] bg-[#fbf0d9] p-5 shadow-[0_30px_90px_rgba(86,67,31,0.1)] sm:p-8 lg:min-h-[540px] lg:p-10">
      <div className="mb-6 flex items-center justify-between text-[10px] font-black uppercase tracking-[0.13em] text-[#64766d]">
        <span>One product, both sides of the booking</span>
        <span className="rounded-full bg-white px-3 py-1.5 text-[#0f6b4f] shadow-sm">Live experience</span>
      </div>
      <div className="hidden md:block">
        <div className="ml-auto w-[92%]"><DashboardPreview /></div>
        <div className="absolute bottom-[-28px] left-3 lg:bottom-[-34px] lg:left-7"><BookingPreview /></div>
      </div>
      <div className="md:hidden">
        <BookingPreview />
        <div className="mt-5 grid grid-cols-3 gap-2">
          {[["Bookings", "8"], ["Deposits", "₦85k"], ["Open slots", "12"]].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-white bg-white/80 p-3 text-center"><strong className="block text-sm">{value}</strong><span className="mt-1 block text-[8px] font-semibold text-[#64766d]">{label}</span></div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className={`${bodyFont.className} min-h-screen bg-[#fffdf8] text-[#102b21]`}>
      <header className="sticky top-0 z-50 border-b border-[#e8ece7] bg-[#fffdf8]/90 shadow-[0_8px_30px_rgba(24,51,39,0.04)] backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" aria-label="Bookie home"><Wordmark /></Link>
          <nav className="hidden items-center gap-7 text-sm font-semibold text-[#50655b] md:flex" aria-label="Main navigation">
            <a href="#how-it-works" className="hover:text-[#0f6b4f]">How it works</a>
            <a href="#features" className="hover:text-[#0f6b4f]">Features</a>
            <a href="#ai-front-desk" className="hover:text-[#0f6b4f]">AI front desk</a>
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link href="/login" className="hidden px-3 py-2 text-sm font-bold text-[#17382b] hover:text-[#0f6b4f] sm:inline-flex">Sign in</Link>
            <Link href="/register" className="inline-flex min-h-11 items-center rounded-xl bg-[#0f6b4f] px-4 text-xs font-black text-white shadow-[0_12px_26px_rgba(15,107,79,0.18)] transition hover:-translate-y-0.5 hover:bg-[#0a563f] sm:text-sm">Create your page</Link>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-20 pt-14 sm:px-8 sm:pt-20 lg:grid-cols-[0.88fr_1.12fr] lg:gap-16 lg:pb-28">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#dce7df] bg-white px-3 py-1.5 text-[11px] font-black uppercase tracking-[0.1em] text-[#0f6b4f]"><ShieldCheck size={14} weight="fill" /> Simple online booking</span>
          <h1 className={`${displayFont.className} mt-6 text-[clamp(3.3rem,6.2vw,5.35rem)] font-normal leading-[0.94] tracking-[-0.045em] text-[#092d20]`}>One link for availability, bookings and deposits.</h1>
          <p className="mt-6 max-w-xl text-base font-medium leading-7 text-[#52675d] sm:text-lg sm:leading-8">Set up what people can book, share your Bookie link, and let clients choose a real available time and pay their deposit—without the back-and-forth.</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/register" className="group inline-flex min-h-14 items-center justify-between gap-5 rounded-xl bg-[#0f6b4f] px-5 text-sm font-black text-white shadow-[0_18px_36px_rgba(15,107,79,0.2)] transition hover:-translate-y-0.5 hover:bg-[#0a563f] sm:min-w-[230px]">Create your booking page <span className="grid h-8 w-8 place-items-center rounded-full bg-white/15"><ArrowRight size={16} weight="bold" /></span></Link>
            <Link href="/book/bookie-live-demo" className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl border border-[#bfd0c5] bg-white px-5 text-sm font-black text-[#0f6b4f] transition hover:bg-[#f1f7f3]">View a live booking page <ArrowRight size={15} weight="bold" /></Link>
          </div>
          <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs font-bold text-[#60766a]">
            <span className="flex items-center gap-2"><Check size={15} weight="bold" className="text-[#0f6b4f]" /> No customer account</span>
            <span className="flex items-center gap-2"><Check size={15} weight="bold" className="text-[#0f6b4f]" /> Paystack deposits</span>
            <span className="flex items-center gap-2"><Check size={15} weight="bold" className="text-[#0f6b4f]" /> Real availability</span>
          </div>
        </div>
        <ProductShowcase />
      </section>

      <section className="border-y border-[#eee5d2] bg-[#fbf5e8]">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-5 px-5 py-7 text-center sm:px-8 lg:flex-row lg:justify-between lg:text-left">
          <div><p className="text-[10px] font-black uppercase tracking-[0.16em] text-[#0f6b4f]">Made for anything people can book</p><p className="mt-1 text-sm font-bold text-[#263f34]">Time, services, sessions, spaces and experiences.</p></div>
          <div className="flex flex-wrap justify-center gap-2 text-xs font-bold text-[#40594e]">
            {["Appointments", "Consultations", "Classes", "Studios", "Home services"].map((item) => <span key={item} className="rounded-full border border-[#e2d8c4] bg-white px-3 py-2">{item}</span>)}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-7xl scroll-mt-20 px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-2xl text-center"><p className="text-[11px] font-black uppercase tracking-[0.16em] text-[#0f6b4f]">How it works</p><h2 className={`${displayFont.className} mt-3 text-5xl font-normal leading-[1.02] tracking-[-0.035em] sm:text-6xl`}>From enquiry to confirmed booking.</h2><p className="mt-4 text-base font-medium leading-7 text-[#60766a]">A clear path for you and the people booking with you.</p></div>
        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {steps.map(({ icon: Icon, number, title, description }) => (
            <article key={number} className="rounded-2xl border border-[#e2e8e3] bg-white p-6 shadow-[0_18px_45px_rgba(20,55,40,0.06)]">
              <div className="flex items-start justify-between"><span className="grid h-14 w-14 place-items-center rounded-2xl bg-[#fbefd9] text-[#8a5525]"><Icon size={27} weight="duotone" /></span><span className="text-4xl font-black text-[#eadcbe]">{number}.</span></div>
              <h3 className="mt-7 text-xl font-black tracking-[-0.03em]">{title}</h3><p className="mt-3 text-sm font-medium leading-6 text-[#60766a]">{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="features" className="scroll-mt-20 bg-[#f3f7f3] py-24">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-[1.08fr_0.92fr]">
            <div className="rounded-[2rem] bg-[#e5eee7] p-4 sm:p-7"><DashboardPreview /></div>
            <div><p className="text-[11px] font-black uppercase tracking-[0.16em] text-[#0f6b4f]">Your business side</p><h2 className={`${displayFont.className} mt-3 text-5xl font-normal leading-[1.02] tracking-[-0.035em] sm:text-6xl`}>See what is booked, paid and still available.</h2><p className="mt-5 text-base font-medium leading-7 text-[#60766a]">Bookie keeps your services, staff, availability, bookings and deposit status together—so you can stop managing appointments across scattered messages.</p><div className="mt-7 grid gap-3 sm:grid-cols-2">{["One organised dashboard", "Live schedule visibility", "Staff and service setup", "Payment status at a glance"].map((item) => <div key={item} className="flex items-center gap-3 rounded-xl border border-[#dce6df] bg-white px-4 py-3 text-sm font-bold"><CheckCircle size={19} weight="fill" className="shrink-0 text-[#0f6b4f]" />{item}</div>)}</div></div>
          </div>

          <div className="mt-20 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {featureCards.map(({ icon: Icon, title, description, badge }) => (
              <article key={title} className="rounded-2xl border border-[#dfe7e1] bg-white p-6">
                <div className="flex items-start justify-between gap-3"><span className="grid h-12 w-12 place-items-center rounded-xl bg-[#e9f3ec] text-[#0f6b4f]"><Icon size={24} weight="duotone" /></span>{badge && <span className="rounded-full bg-[#fff0df] px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.08em] text-[#8a5525]">{badge}</span>}</div>
                <h3 className="mt-6 text-lg font-black tracking-[-0.025em]">{title}</h3><p className="mt-3 text-sm font-medium leading-6 text-[#60766a]">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="ai-front-desk" className="mx-auto max-w-7xl scroll-mt-20 px-5 py-24 sm:px-8">
        <div className="overflow-hidden rounded-[2rem] bg-[#082f22] text-white">
          <div className="grid gap-10 px-7 py-10 sm:px-12 sm:py-14 lg:grid-cols-[0.9fr_1.1fr] lg:px-16 lg:py-16">
            <div><span className="inline-flex items-center gap-2 rounded-full bg-[#ffdfcc] px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.12em] text-[#7b401d]"><Sparkle size={14} weight="fill" /> Coming soon</span><h2 className={`${displayFont.className} mt-6 text-5xl font-normal leading-[1.02] tracking-[-0.035em] sm:text-6xl`}>An AI front desk that knows when to call you in.</h2><p className="mt-5 max-w-xl text-base font-medium leading-7 text-white/70">Bookie will handle routine enquiries, check real availability, guide people into the booking flow, and hand unusual requests to you with the context attached.</p></div>
            <div className="grid gap-3 self-center">
              {["Answer common questions through messaging channels", "Use your real services, staff and availability", "Prepare bookings without bypassing confirmation", "Pause immediately when a human takes over"].map((item) => <div key={item} className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.06] px-5 py-4 text-sm font-bold"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#0f6b4f]"><Check size={17} weight="bold" /></span>{item}</div>)}
              <div className="mt-2 flex items-center gap-3 text-sm font-semibold text-[#b9d6c8]"><Robot size={23} weight="duotone" /> Human handoff and booking safeguards from day one.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-5 pb-24 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-8 rounded-[2rem] border border-[#eadfc9] bg-[#fbf0d9] px-7 py-12 text-center lg:flex-row lg:px-14 lg:text-left">
          <div><p className="text-[11px] font-black uppercase tracking-[0.16em] text-[#0f6b4f]">Ready when you are</p><h2 className={`${displayFont.className} mt-3 max-w-3xl text-5xl font-normal leading-[1.02] tracking-[-0.035em] sm:text-6xl`}>Spend less time arranging bookings in messages.</h2><p className="mt-4 text-base font-medium text-[#60766a]">Create your Bookie page and start sharing one clear link.</p></div>
          <Link href="/register" className="inline-flex min-h-14 shrink-0 items-center justify-center gap-2 rounded-xl bg-[#0f6b4f] px-7 text-sm font-black text-white shadow-[0_18px_35px_rgba(15,107,79,0.18)] transition hover:-translate-y-0.5 hover:bg-[#0a563f]">Create your booking page <ArrowRight size={17} weight="bold" /></Link>
        </div>
      </section>

      <footer className="bg-[#07281d] px-5 py-10 text-white sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-7 sm:flex-row sm:items-center sm:justify-between"><Wordmark light /><div className="flex flex-wrap gap-6 text-sm font-semibold text-white/65"><a href="#how-it-works" className="hover:text-white">How it works</a><a href="#features" className="hover:text-white">Features</a><a href="#ai-front-desk" className="hover:text-white">AI front desk</a><Link href="/login" className="hover:text-white">Sign in</Link></div><span className="text-xs font-semibold text-white/45">© 2026 Bookie</span></div>
      </footer>
    </main>
  );
}
