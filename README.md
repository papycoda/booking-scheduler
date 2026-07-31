# Bookie - Appointment Booking Made Simple

**Bookie** is a booking and payment system for Nigerian small businesses. If you run a salon, barbershop, spa, consulting service, or any business that takes appointments, Bookie helps you:

- Accept bookings online 24/7
- Let customers choose services and time slots
- Collect payments securely via Paystack
- Receive money directly to your bank account
- Manage everything from one simple dashboard

---

## What You'll Need

Before you start, make sure you have:

**For your computer (Manual Setup):**
- **Python 3.12 or newer** — [Download here](https://www.python.org/downloads/)
- **Node.js 20 or newer** — [Download here](https://nodejs.org/)
- **Git** — [Download here](https://git-scm.com/downloads)
- A code editor (like [VS Code](https://code.visualstudio.com/))

**For Docker-backed local services (Recommended):**
- **Docker Desktop** — [Download here](https://www.docker.com/products/docker-desktop/)
- Docker starts PostgreSQL and Redis. Run the backend and frontend from your local Python and Node installs.

**For the app to work:**
- **Paystack account** — [Sign up free](https://paystack.co/) (for collecting payments)
- (Optional) **Resend account** — [Sign up free](https://resend.com/) (for email notifications)
- (Optional) **Meta WhatsApp Business account** — [Learn more](https://developers.facebook.com/docs/whatsapp/) (for WhatsApp notifications)

> **Using Docker?** Skip manual PostgreSQL and Redis setup. Docker handles those services only.
- **Paystack account** — [Sign up free](https://paystack.co/) (for collecting payments)
- (Optional) **Resend account** — [Sign up free](https://resend.com/) (for email notifications)
- (Optional) **Meta WhatsApp Business account** — [Learn more](https://developers.facebook.com/docs/whatsapp/) (for WhatsApp notifications)

---

## Quick Start (5-Minute Setup)

### Step 1: Get the Code

Open your terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
git clone https://github.com/papycoda/booking-scheduler.git
cd booking-scheduler
```

### Step 2: Install Dependencies

**Backend (Python):**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend (Node.js):** (open a new terminal window)
```bash
cd frontend
npm install
```

### Step 3: Set Up Environment Variables

Create a file named `.env` in the `backend` folder with these settings:

**Windows (PowerShell):**
```powershell
cd backend
copy .env.example .env
```

**macOS/Linux (bash/sh):**
```bash
cd backend
cp .env.example .env
```

Now open `.env` in a text editor and fill in your details:

| Setting | What to Put | Where to Get It |
|---------|-------------|-----------------|
| `SECRET_KEY` | A long random string (min 32 characters) | Make one up or use `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FRONTEND_URL` | Your frontend URL | For local dev: `http://localhost:3000` |
| `ENVIRONMENT` | `development` | — |
| `DEMO_MODE` | `true` or `false` | Set to `true` to test payment flow without Paystack (development only) |
| `DEMO_ADMIN_EMAILS` | Comma-separated admin emails | E.g., `test@gmail.com,admin@example.com` — only these emails can use demo mode |
| `DATABASE_URL` | PostgreSQL connection string | Local Docker: `postgresql+asyncpg://booking_scheduler:booking_scheduler@127.0.0.1:5433/booking_scheduler` |
| `REDIS_URL` | Redis connection string | Local Docker: `redis://127.0.0.1:6379` |
| `PAYSTACK_SECRET_KEY` | Your Paystack secret key | From [Paystack Dashboard → Settings → API Keys](https://dashboard.paystack.co/#/settings/keys) |
| `PAYSTACK_WEBHOOK_SECRET` | Your Paystack webhook secret | From [Paystack Dashboard → Settings → API Keys → Webhook](https://dashboard.paystack.co/#/settings/keys) |
| `RESEND_API_KEY` | Your Resend API key | From [Resend Dashboard → API Keys](https://resend.com/api-keys) (optional) |
| `FROM_EMAIL` | Sender email address | Your verified email in Resend (optional) |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | From the Twilio Console (optional until WhatsApp is connected) |
| `TWILIO_AUTH_TOKEN` | Twilio auth token used for sending and webhook verification | From the Twilio Console |
| `TWILIO_WHATSAPP_FROM_NUMBER` | Twilio WhatsApp sender in E.164 format | From the Twilio WhatsApp Sandbox or approved sender |

### Step 4: Set Up the Database

Run the database migration to create all tables:

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

**macOS/Linux (bash/sh):**
```bash
export PYTHONPATH='backend'
python -m alembic -c backend/alembic.ini upgrade head
```

### Step 5: Start the Servers

**Backend (Terminal 1):**

Windows (PowerShell):
```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend
```

macOS/Linux (bash/sh):
```bash
export PYTHONPATH='backend'
python -m uvicorn app.main:app --reload --app-dir backend
```

You should see: `Application startup complete` running at `http://127.0.0.1:8000`

**Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## Demo Mode (Testing Without Paystack)

Demo mode lets you test the complete payment flow without needing Paystack credentials. It simulates the entire booking-to-payment lifecycle—perfect for development, presentations, or exploring the app.

### What Demo Mode Does

When enabled:
- Booking creation redirects to a mock payment page (`/demo/pay`)
- Clicking "Complete Demo Payment" simulates a successful Paystack transaction
- Booking status changes to "confirmed"
- Payment is recorded as successful in the database
- Payout is queued (if using platform_collected mode)
- Confirmation notifications are sent (if configured)

**What it doesn't do:**
- No real money is charged
- No actual Paystack transaction occurs
- Webhook signature verification is bypassed

### How to Enable Demo Mode

In your `backend/.env` file, set:

```env
DEMO_MODE=true
DEMO_ADMIN_EMAILS=test@gmail.com,admin@example.com
```

**⚠️ Security Note:** Demo mode is **admin-only**. Only emails listed in `DEMO_ADMIN_EMAILS` can access demo payments. All other bookings will proceed to real Paystack (and fail if Paystack credentials aren't configured).

Then restart the backend server.

**Configuration details:**
- `DEMO_MODE=true` — Enables demo mode functionality
- `DEMO_ADMIN_EMAILS` — Comma-separated list of authorized emails (case-insensitive)
- If `DEMO_ADMIN_EMAILS` is empty or not set, demo mode is effectively disabled for everyone
- Non-admin bookings silently fall back to real Paystack

### Use Cases

| Use Case | Why Demo Mode Helps |
|----------|---------------------|
| **Development** | Test payment flow without API keys |
| **Presentations** | Demo the app live without real transactions |
| **Onboarding** | Let stakeholders explore before integrating Paystack |
| **CI/CD Testing** | Automated tests without external dependencies |

> **⚠️ Important:** Demo mode is for **development and testing only**. Never enable it in production—you'd be accepting bookings without actually collecting payments!

### Testing the Demo Flow

1. Enable demo mode and add your email to `DEMO_ADMIN_EMAILS` in `.env`, then restart backend
2. Go through the booking flow on the public page using an email from your admin list
3. When redirected to `/demo/pay?reference=...`, click "Complete Demo Payment"
4. Verify the booking shows as "confirmed" on the verify page

---

## Docker-Backed Local Setup

**Prefer Docker for dependencies?** This project's `docker-compose.yml` starts PostgreSQL and Redis only. Run the backend and frontend from your local Python and Node installs.

**What you'll need:**
- **Docker Desktop** — [Download here](https://www.docker.com/products/docker-desktop/) (free)

### Step 1: Get the Code

```bash
git clone https://github.com/papycoda/booking-scheduler.git
cd booking-scheduler
```

### Step 2: Create Backend Environment File

**Windows (PowerShell):**
```powershell
# In the project root, create backend\.env from the example
copy backend\.env.example backend\.env
```

**macOS/Linux (bash/sh):**
```bash
# In the project root, create backend/.env from the example
cp backend/.env.example backend/.env
```

Open `backend/.env` in a text editor and fill in these local service values:

```env
SECRET_KEY=your-random-secret-key-min-32-chars
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://booking_scheduler:booking_scheduler@127.0.0.1:5433/booking_scheduler
REDIS_URL=redis://127.0.0.1:6379
PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_WEBHOOK_SECRET=your-paystack-webhook-secret
# Optional: Resend for emails
RESEND_API_KEY=your-resend-api-key
FROM_EMAIL=noreply@yourdomain.com
# Optional: WhatsApp
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM_NUMBER=
```

### Step 3: Start PostgreSQL and Redis

```bash
docker-compose up -d postgres redis
```

This starts:
- **PostgreSQL database** on host port `5433`
- **Redis cache** on host port `6379`

Postgres uses `5433` to avoid conflicts with local PostgreSQL installs that commonly use `5432`.

### Step 4: Run Database Migrations

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

**macOS/Linux (bash/sh):**
```bash
export PYTHONPATH='backend'
python -m alembic -c backend/alembic.ini upgrade head
```

Do not use `docker-compose exec backend`; Compose does not define a `backend` service.

### Step 5: Start the App

**Windows (PowerShell):**
```powershell
# Terminal 1: backend API
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend

# Terminal 2: frontend
cd frontend
npm run dev
```

**macOS/Linux (bash/sh):**
```bash
# Terminal 1: backend API
export PYTHONPATH='backend'
python -m uvicorn app.main:app --reload --app-dir backend

# Terminal 2: frontend
cd frontend
npm run dev
```

The API runs at `http://127.0.0.1:8000`; the frontend runs at `http://localhost:3000`.

### Stop Everything

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f redis
```

---

## Using Bookie

### For Business Owners

**1. Create Your Account**

Visit `http://localhost:3000/register` and sign up.

**2. Set Up Your Business**

After logging in, go to your dashboard and:

- Add your business name, logo, and description
- Set your working hours and availability
- Add services you offer (with prices and duration)
- Add staff members (if you have a team)
- Connect your Paystack account for payments
- Add your bank account for payouts

**3. Get Your Booking Link**

Once set up, you'll get a custom booking link like:
```
http://localhost:3000/book/your-business-name
```

Share this link with customers via WhatsApp, Instagram, email, or add it to your website.

**4. Manage Bookings**

In your dashboard, you can:
- See all upcoming bookings
- View booking history
- Accept or reject reschedule requests
- Track payments and payouts
- Export reports

### For Customers

**1. Find the Business**

Ask the business for their booking link, or visit the public booking page.

**2. Choose a Service**

Browse available services, see prices, and select what you need.

**3. Pick a Time**

See available time slots and choose what works for you.

**4. Book and Pay**

Enter your details and pay securely with Paystack. You'll receive a confirmation.

**5. Reschedule if Needed**

Need to change your appointment? Just click the reschedule link in your confirmation email (if enabled).

---

## Features

| Feature | Description |
|---------|-------------|
| **Online Bookings 24/7** | Customers can book anytime, no phone calls needed |
| **Secure Payments** | Integrated with Paystack for safe transactions |
| **Automatic Payouts** | Money goes straight to your bank account |
| **Deposit Support** | Optionally collect deposits to hold bookings |
| **Staff Management** | Multiple team members with individual schedules |
| **Service Catalog** | Define your services with prices and duration |
| **Rescheduling** | Easy reschedule requests with approval workflow |
| **Notifications** | Email and WhatsApp reminders (optional) |
| **Multi-Business** | Run multiple businesses from one account |

---

## Deployment Guide

### Deploying to Production

**Option 1: Vercel (Recommended for Frontend)**

```bash
cd frontend
npm run build
vercel deploy
```

**Option 2: Railway/Render (Backend)**

1. Push your code to GitHub
2. Connect your repository to [Railway](https://railway.app) or [Render](https://render.com)
3. Add environment variables in their dashboard
4. Deploy!

**Important:** When deploying, update:
- `FRONTEND_URL` to your production domain
- `DATABASE_URL` to your production database
- `PAYSTACK_WEBHOOK_SECRET` to your production webhook secret
- Configure Paystack webhook URL to point to your backend

---

## Troubleshooting

### Common Issues

**Problem:** Backend won't start
- **Check:** Python version is 3.12+
- **Check:** All dependencies installed with `pip install -r requirements.txt`
- **Check:** Database URL is correct in `.env`

**Problem:** Frontend won't start
- **Check:** Node.js version is 20+
- **Check:** Ran `npm install` in the frontend folder
- **Check:** No other app is using port 3000

**Problem:** Database connection error
- **Check:** Database is running and accessible
- **Check:** `DATABASE_URL` format is correct: `postgresql://user:password@host:port/database`
- **Check:** Firewall allows connections

**Problem:** Payments not working
- **Check:** Paystack keys are correct
- **Check:** Using test keys for testing, live keys for production
- **Check:** Webhook URL is configured in Paystack dashboard

**Problem:** Webhook not being received
- **Check:** Using ngrok or similar for local testing
- **Check:** Paystack webhook URL points to `https://your-domain.com/api/webhooks/paystack`
- **Check:** `PAYSTACK_WEBHOOK_SECRET` matches Paystack dashboard

**Docker Issues:**

**Problem:** Docker won't start
- **Check:** Docker Desktop is running
- **Check:** No other app is using port 5433 or 6379
- **Windows:** Make sure WSL 2 is installed

**Problem:** `docker-compose up` fails with database errors
- **Check:** Run `docker-compose down -v` then `docker-compose up -d` to reset volumes
- **Check:** No other PostgreSQL is running on port 5433

**Problem:** Can't access frontend/backend
- **Check:** Start backend and frontend locally; Docker only starts Postgres and Redis
- **Check:** Run `docker-compose ps` to verify Postgres and Redis are healthy
- **Check:** `docker-compose logs` shows no database or Redis errors

---

## Need Help?

- **Documentation:** See `CLAUDE.md` for technical details
- **Issues:** Open an issue on [GitHub](https://github.com/papycoda/booking-scheduler/issues)
- **Paystack Support:** [https://paystack.co/support](https://paystack.co/support)

---

## License

This project is open source and available under the MIT License.

---

## What's Next?

Bookie is continuously improving. Upcoming features:

- SMS notifications
- Calendar sync (Google Calendar, Outlook)
- Advanced reporting and analytics
- Mobile apps
- Multi-language support

Want to contribute? We welcome pull requests!

---

Made with ❤️ for Nigerian small businesses
