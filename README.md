# Booking Scheduler

Production-ready multi-tenant appointment booking SaaS.

Current status: Phase 1 backend foundation.


You are working on the Bookie repo:

https://github.com/papycoda/booking-scheduler

Bookie is a multi-tenant booking and payments SaaS for Nigerian small businesses. The latest commit added automated payouts, retry logic, payout account setup, webhook verification, unpaid booking expiry, and fee caps.

Your task is to fix the QA/security issues found in the second-pass audit.

Do not add unrelated features. Do not redesign unrelated pages. Focus only on payout safety, webhook correctness, payout review rules, account masking, and the related tests.

## Current high-risk areas

The latest commit is:

`c12b4771b50a676afacd37c6732a392cc6f9febc`

Commit message:

`feat: add automated payout system`

The risky files are likely:

* `backend/app/services/settlement_service.py`
* `backend/app/routers/bookings.py`
* `backend/app/routers/webhooks.py`
* `backend/app/services/payment_lifecycle_service.py`
* `backend/app/routers/tenants.py`
* `backend/app/schemas/tenant.py`
* `backend/app/schemas/dashboard.py`
* `frontend/app/dashboard/settings/page.tsx`
* `frontend/lib/api.ts`
* related tests under `backend/tests/`

## Fix 1 — Correct payout retry logic

Product rule:

A payout should have:

* Initial payout attempt
* 3 automatic retries after temporary provider/network failure
* Then move to manual review

The current implementation likely moves to review too early because `payout_attempt_count` is incremented before checking retry limits.

Fix the logic so the actual behavior is:

1. First attempt fails → schedule retry 1 after 5 minutes
2. Retry 1 fails → schedule retry 2 after 30 minutes
3. Retry 2 fails → schedule retry 3 after 2 hours
4. Retry 3 fails → set `settlement_status = "needs_review"` and `payout_review_reason = "retry_limit_reached"`

Use clear constants so the code is not ambiguous.

Recommended naming:

```python
PAYOUT_RETRY_DELAYS = (
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
)
MAX_PAYOUT_ATTEMPTS = 1 + len(PAYOUT_RETRY_DELAYS)
```

`payout_attempt_count` should mean total attempts, including the initial attempt.

After a failed attempt:

* If `payout_attempt_count < MAX_PAYOUT_ATTEMPTS`, set `settlement_status = "failed"` and schedule `next_payout_attempt_at` using the correct retry delay.
* If `payout_attempt_count >= MAX_PAYOUT_ATTEMPTS`, set `settlement_status = "needs_review"`, clear `next_payout_attempt_at`, and set `payout_review_reason = "retry_limit_reached"`.

Add tests for all four failure stages.

Required tests:

* first failure schedules 5-minute retry
* second failure schedules 30-minute retry
* third failure schedules 2-hour retry
* fourth failure moves to `needs_review`
* successful payout clears `last_payout_error`, clears `payout_review_reason`, stores provider transfer code, and sets status to `paid`

## Fix 2 — Prevent tenant owners from approving review-required payouts

Current problem:

The dashboard exposes tenant-facing endpoints like:

* `POST /dashboard/payouts/{payment_id}/approve`
* `POST /dashboard/payouts/{payment_id}/retry`

If tenant owners can approve a payout marked `needs_review`, then first-payout review and risky-payout review are meaningless.

Product rule:

Tenant/business users must NOT approve review-required payouts.

Tenant users can:

* view their payout status
* see that a payout is under review
* retry a payout only when it is safe and allowed
* update payout bank details

Tenant users must NOT:

* approve first payout review
* approve risky payout review
* bypass `needs_review`

Implementation requirements:

1. Remove or restrict tenant-facing `approve` endpoint.
2. If an endpoint remains, it must require a platform/admin role, not `tenant_owner`.
3. Tenant-facing retry should only work for retryable failed payouts.
4. Retry must NOT work when `settlement_status == "needs_review"`.
5. Add structured error responses.

Expected behavior:

* If tenant owner calls approve endpoint, return `403 FORBIDDEN`.
* If tenant owner tries to retry a payout in `needs_review`, return `409 CONFLICT` with:

```json
{
  "error": "PAYOUT_REVIEW_REQUIRED",
  "message": "This payout needs manual review before it can be sent."
}
```

Add tests for:

* tenant owner cannot approve first payout
* tenant owner cannot retry `needs_review` payout
* tenant owner can see payout status
* platform admin can approve if platform-admin support already exists
* if platform-admin support does not exist yet, leave a clear TODO and make the tenant-facing approval impossible for now

Do not invent a fake admin dashboard if one does not exist. Just protect the backend correctly.

## Fix 3 — Prevent expired bookings from being resurrected by late Paystack webhooks

Current problem:

Unpaid bookings expire after 15 minutes. The scheduler sets:

* `booking.status = "expired"`
* `payment.status = "expired"`

But if Paystack later sends a `charge.success` webhook, the webhook can set:

* `payment.status = "success"`
* `booking.status = "confirmed"`

That resurrects an expired booking and can create double-booking risk.

Fix:

In `backend/app/routers/webhooks.py`, before confirming payment and booking, explicitly reject expired records.

Expected logic:

```python
if payment.status == "expired" or booking.status == "expired":
    logger.warning(...)
    return JSONResponse(status_code=200, content={"status": "ignored_expired"})
```

Do not return 4xx or 5xx to Paystack. Always return 200 for validly signed webhooks, even when ignored.

Important:

* Still verify signature first.
* Still verify reference, amount, and currency.
* Do not confirm expired bookings.
* Do not queue payouts for expired payments.
* Do not send confirmation notifications for expired bookings.

Add tests for:

* expired payment + valid webhook remains expired
* expired booking + valid webhook remains expired
* expired booking does not send confirmation notification
* expired booking does not queue payout
* valid pending payment still confirms normally

## Fix 4 — Add row-level locking / concurrency safety for automated payout processing

Current problem:

`process_due_payouts` selects due payouts and loops over them. If multiple workers run, two workers can pick the same payout.

Fix:

Use database-level locking when selecting due payouts.

Implementation requirements:

1. Select due payout rows using `FOR UPDATE SKIP LOCKED`.
2. Only select payments with:

   * `status == "success"`
   * `collection_mode == "platform_collected"`
   * `settlement_status IN ("queued", "failed")`
   * `next_payout_attempt_at IS NULL OR next_payout_attempt_at <= now`
3. Mark each selected payout as `processing` before calling Paystack.
4. Avoid double transfer attempts from multiple workers.
5. Keep idempotent provider references.

Recommended approach:

* In `process_due_payouts`, use:

```python
select(Payment)
.where(...)
.order_by(Payment.created_at)
.limit(limit)
.with_for_update(skip_locked=True)
```

* Be careful with transaction boundaries.
* Do not hold locks while doing a slow external HTTP call if avoidable.
* A safer pattern is:

  1. lock due rows
  2. mark selected rows as `processing`
  3. commit
  4. call Paystack for each selected payout by ID
  5. update result

If this requires a small refactor, do it cleanly.

Add tests for:

* due payout selection uses lock/skip locked where practical
* processing status is not selected again
* already paid payout is not processed again
* failed payout with future `next_payout_attempt_at` is not processed
* failed payout with due `next_payout_attempt_at` is processed

## Fix 5 — Mask payout account numbers in frontend and API responses

Current issue:

The API and frontend expose full payout account number and internal provider codes.

Product rule:

Users should see:

* account name
* bank name
* masked account number, e.g. `******2734`

Users should NOT see:

* full account number after save
* `paystack_subaccount_code`
* `payout_recipient_code`
* other provider/internal routing codes

Backend changes:

1. Update tenant/payment status response schemas so dashboard responses expose:

   * `payout_account_name`
   * `payout_bank_name`
   * `masked_payout_account_number`
   * `payment_setup_status`
   * `payments_enabled`
   * `payout_ready`
   * `onboarded` if still needed

2. Stop returning these fields to the frontend:

   * `paystack_subaccount_code`
   * `payout_recipient_code`

3. Keep provider codes stored only server-side.

4. Add a helper like:

```python
def mask_account_number(account_number: str | None) -> str | None:
    if not account_number:
        return None
    return f"******{account_number[-4:]}"
```

Frontend changes:

1. Update `frontend/lib/api.ts` types.
2. Update dashboard settings page to display masked account number.
3. Do not render full account number after save.
4. Ensure edit mode can still show empty fields or require re-entry. Do not prefill the full saved account number if the API no longer returns it.
5. Use simple copy:

   * “Payout account saved”
   * “Money from paid bookings will be sent to:”
   * show account name, bank, masked account number

Add tests where practical:

* API returns masked account number
* API does not return provider codes
* frontend type no longer expects provider codes

## Fix 6 — First-payout review should not repeatedly flag every payout

Current problem:

The first-payout logic checks previous payouts with `settlement_status == "paid"`. If the first payout is still under review, the next payout also becomes `first_payout`.

Better rule:

A tenant should only need first-payout review once.

Implement one of these options:

Preferred option:
Add tenant-level fields:

* `first_payout_review_completed_at TIMESTAMPTZ NULL`
* optionally `first_payout_review_completed_by UUID NULL`

Then:

* If tenant has no `first_payout_review_completed_at`, queue first eligible payout as `needs_review` with `payout_review_reason = "first_payout"`.
* When platform admin approves the first payout, set `first_payout_review_completed_at`.
* Future payouts should not be flagged as first payout.

If you do not want to add the tenant field yet, use a safer fallback:

Count previous payouts with any of these statuses:

* `paid`
* `queued`
* `processing`
* `needs_review`
* `failed`

But the tenant-level flag is cleaner and preferred.

Add migration for the tenant field if implemented.

Add tests:

* first payout for new tenant becomes `needs_review`
* second payout while first is under review does not also become `first_payout`
* after review is completed, future payouts queue automatically

## Fix 7 — Payout setup should return clear verification feedback

Current behavior:

If bank lookup or transfer recipient creation fails, the system silently stores some details and sets `payment_setup_status = "not_started"`.

This is safe technically but bad UX.

Product rule:

Users should know what happened.

Expected API response should include:

* `payout_ready: false`
* `payment_setup_status: "not_started"` or better `"verification_failed"` if you add that status
* a user-safe message or reason like:

  * “We saved your details, but could not verify this payout account yet. Please check the bank name and account number.”

Implementation options:

Option A:
Add `payout_setup_message` to `PaystackStatusResponse`.

Option B:
Return structured HTTP error when verification fails and do not save unverifiable details.

Preferred for Bookie right now:

Save the details, but return a warning message.

Do not expose raw Paystack errors to the user.

Add tests:

* invalid bank returns user-safe message
* recipient creation failure does not expose raw provider error
* valid payout setup returns `payout_ready = true`

## Fix 8 — Keep product copy simple and remove provider language

Review the dashboard Payments/Payout page.

Make sure the user-facing UI does not contain:

* subaccount
* direct split
* routing payments
* settlement configuration
* provider setup
* transfer recipient
* Paystack setup

The user should only see:

* “Deposits are turned on”
* “Customers can pay through your booking link.”
* “Payout account needed”
* “Add the bank account where you want to receive your money.”
* “Payout account saved”
* “Money from paid bookings will be sent to this account.”

Do not add advanced payment setup back.

## Fix 9 — Add tests for the full payment lifecycle

Add or update tests covering:

### Webhook tests

* invalid signature returns 400
* signed non-charge event returns 200 ignored
* signed charge.success with wrong amount returns 200 ignored
* signed charge.success with wrong currency returns 200 ignored
* signed charge.success for expired payment returns 200 ignored and does not confirm booking
* signed charge.success for pending payment confirms booking and queues payout correctly

### Payout tests

* first payout requires review
* tenant owner cannot approve review payout
* retry schedule is correct
* retry limit sends payout to review
* payout success marks as paid
* payout missing account goes to `needs_setup`
* no double processing with `processing` status

### Payment lifecycle tests

* unpaid pending booking expires after 15 minutes
* expired payment cannot be confirmed later by webhook
* expired booking releases slot only if the unique active slot index excludes expired bookings

### API response tests

* payout account number is masked
* provider codes are not returned to frontend status response
* invalid payout setup returns user-safe warning

## Definition of done

The work is complete only when:

1. Tenant owners cannot approve their own manual-review payouts.
2. First payout review is meaningful and cannot be bypassed.
3. Expired bookings cannot be resurrected by late Paystack webhooks.
4. Automated payouts support initial attempt + 3 retries, then review.
5. Payout processor is safe against concurrent workers.
6. Dashboard/API never expose full payout account number after save.
7. Provider codes are not returned to the frontend.
8. Payout setup errors are clear and user-safe.
9. Tests cover the above cases.
10. All existing tests pass.

Run:

```bash
cd backend
python -m compileall app
pytest
alembic upgrade head
```

Then run frontend checks:

```bash
cd frontend
npm install
npm run lint
npm run build
```

If any command fails, fix it before finishing.

## Important constraints

* Do not use sync DB calls inside the FastAPI backend.
* Do not return raw provider errors to users.
* Do not log secrets, tokens, raw Paystack keys, or full account numbers.
* Do not reintroduce advanced payment setup into the user-facing dashboard.
* Do not change unrelated product flows.
* Do not silently make risky product decisions. Leave a TODO and explain if something is ambiguous.
* Keep all error responses structured:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable message."
}
```

## Expected commit message

Use this commit message:

`fix: harden payout automation and payment lifecycle safety`
