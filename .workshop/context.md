# Project Context
- Project: Day Shift video marketplace
- Stack: React + FastAPI
- Keep the app live on `app.dayshiftnow.me`; ignore the root domain for now.
- The root domain redirect was intentionally left unresolved because it caused SSL/forwarding issues.
- Contact email was updated to `contact@dayshiftnow.me` in the app UI/legal pages.
- The app uses PayPal for payments and still has Stripe-related code paths in the backend.
- reCAPTCHA is present in auth flows and should remain configurable.
- PostHog is optional analytics; the app should tolerate it being absent.
- Resend is used for contact/support email sending.
- `SECRET_KEY` is used by backend auth/session helpers.
- `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are still required for Stripe-backed routes.
- `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` are required for PayPal routes.
- `FORWARD_TO_EMAIL` is used by webhook forwarding/email routing.
- `VITE_POSTHOG_KEY` is optional and should not block startup if missing.
- `RECAPTCHA_SECRET_KEY` and `RECAPTCHA_SITE_KEY` are required only if reCAPTCHA is enabled.
- `RESEND_API_KEY` is required for contact/support email sending.
- `stripe` is a Python dependency used by payment routes.

# Conversation starters
- Check which env vars are truly required at startup vs optional.
- Remove or gate any remaining hard dependency on missing secrets.
- Verify the app still builds and runs with only the needed secrets present.