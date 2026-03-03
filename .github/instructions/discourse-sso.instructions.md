---
applyTo: "**/discourse/**,**/discourse.py"
---

# Discourse SSO

## Overview

Single sign-on integration between Django and the CoMSES Discourse forum. Users authenticate via Django; Discourse trusts Django as the identity provider via HMAC-SHA256 signed payloads.

## Architecture

| File | Purpose |
|------|---------|
| `django/core/discourse.py` | `create_discourse_user()`, `sanitize_username()` |
| `django/core/views.py` | `discourse_sso` view (SSO handshake endpoint) |
| `django/home/signals.py` | `post_save(User)` → syncs profile to Discourse |

## Patterns

### SSO Handshake Flow

```
Discourse → GET /discourse/sso?sso=<payload>&sig=<signature>
  → Django validates HMAC-SHA256(payload, DISCOURSE_SSO_SECRET)
  → Django decodes payload, extracts nonce
  → Django builds return payload: nonce + email + external_id + username + name + avatar_url
  → Django signs return payload with DISCOURSE_SSO_SECRET
  → 302 redirect to Discourse with signed payload
```

### Username Sanitization

`sanitize_username(username, uid=None)` in `django/core/discourse.py`:
- Strips characters Discourse forbids (regex-based, 5 passes)
- Replaces invalid chars with `_`, deduplicates repeated special chars
- Strips invalid leading/trailing characters
- Strips web-like suffixes (`.com`, `.json`, `.html`, etc.)
- Truncates to 60 characters max
- Appends 6-char `shortuuid` fragment for uniqueness when needed

### User Creation

`create_discourse_user(user)` POSTs to Discourse API:
- Sends: `name`, `username` (from `member_profile.discourse_username`), `email`, random password, `active=True`
- Auth: `Api-Key` + `Api-Username` headers
- Triggered by signal when new `MemberProfile` is saved

## Configuration

| Secret | Source | Purpose |
|--------|--------|---------|
| `DISCOURSE_BASE_URL` | settings | Forum base URL |
| `DISCOURSE_SSO_SECRET` | `/run/secrets/discourse_sso_secret` | HMAC signing key |
| `DISCOURSE_API_KEY` | `/run/secrets/discourse_api_key` | API auth for user creation |
| `DISCOURSE_API_USERNAME` | settings | API username (usually `system`) |

## Gotchas

1. **Username collision:** `sanitize_username()` can produce identical outputs for different inputs — the `shortuuid` fragment mitigates but doesn't eliminate this
2. **Signal ordering:** User creation signal fires before email verification — Discourse user may exist before the Django account is confirmed
3. **Secret mounting:** SSO secret is a Docker secret at `/run/secrets/`, not an env var — use `read_secret('discourse_sso_secret')`
