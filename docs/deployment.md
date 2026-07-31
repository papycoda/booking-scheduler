# Deployment

The hosted branch is `main`.

## Render Blueprint

Use the root `render.yaml` Blueprint to provision:

- `booking-scheduler-api` FastAPI web service
- `booking-scheduler-frontend` Next.js web service
- `booking-scheduler-postgres` Postgres database
- `booking-scheduler-redis` Render Key Value instance

Style inspiration uploads are stored in Postgres-backed booking asset rows, so they persist across web service restarts.

Deploy from:

```text
https://dashboard.render.com/blueprint/new?repo=https://github.com/papycoda/booking-scheduler
```

## Required Values

Fill these during Blueprint creation or in each service's Render environment settings:

### API service

```text
FRONTEND_URL=https://<frontend-service>.onrender.com
PAYSTACK_SECRET_KEY=<paystack-secret-key>
PAYSTACK_WEBHOOK_SECRET=<paystack-webhook-secret>
RESEND_API_KEY=<resend-api-key>
FROM_EMAIL=<verified-sender-email>
TWILIO_ACCOUNT_SID=<optional-twilio-account-sid>
TWILIO_AUTH_TOKEN=<optional-twilio-auth-token>
TWILIO_WHATSAPP_FROM_NUMBER=<optional-approved-whatsapp-sender>
```

`SECRET_KEY`, `DATABASE_URL`, and `REDIS_URL` are provided by the Blueprint.
Bookie's v1 link-based booking flow does not require Twilio. If WhatsApp is
enabled later, configure all three Twilio values together.

Paystack signs webhook events with `PAYSTACK_SECRET_KEY`, so a separate webhook
secret is not required. Keep `DEMO_MODE=false` in production.

### Frontend service

```text
NEXT_PUBLIC_API_BASE_URL=https://<api-service>.onrender.com/api/v1
```

## Post-Deploy Checks

1. Open `https://<api-service>.onrender.com/health` and confirm `{"status":"ok"}`.
2. Open `https://<frontend-service>.onrender.com/register`.
3. Register a business owner.
4. In the dashboard, set default deposit, create service, staff, and availability.
5. Open `/book/<slug>` in a private browser window and confirm a client can select a service, slot, and submit without registering.
6. Configure Paystack webhook URL:

```text
https://<api-service>.onrender.com/api/v1/webhooks/paystack
```

7. Run a Paystack sandbox booking and confirm the booking moves from `pending_payment` to `confirmed`.

## Preview versus production

The Blueprint currently uses Render's free instance types so it can be used for
a preview deployment without committing to paid infrastructure. Do not treat
that setup as durable production hosting: free Postgres expires, free Key Value
storage is not persistent, and free web services can restart or sleep.

Before accepting customer bookings, choose paid Postgres, Key Value, API, and
frontend plans, then confirm backups and provider alerts are enabled.
