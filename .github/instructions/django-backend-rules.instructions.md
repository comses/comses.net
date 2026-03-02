---
applyTo: "**/django/**"
---

# Django Backend Rules

## Overview

The Django backend is a synchronous codebase (no async) built on Django 4.2 + Wagtail 6 + DRF. Jinja2 is the primary template engine; Django templates are only used for admin and allauth. See `comses-overview.mdc` for the full stack and app map.

## Architecture

```
django/
  core/           # Foundation: users, events, jobs, permissions, mixins, settings
    settings/     # Layered settings (see table below)
    backends.py   # ComsesObjectPermissionBackend
    mixins.py     # CommonViewSetMixin, SpamCatcherViewSetMixin
    renderers.py  # RootContextHTMLRenderer
    permissions.py
    jinja_config.py  # Jinja2 environment + globals
    jinja2ext.py     # ViteExtension for templates
    pagination.py    # SmallResultSetPagination
    huey.py          # DjangoRedisHuey (reuses django-redis pool)
  library/        # Codebases, releases, peer review, DOI, BagIt
  home/           # Wagtail CMS pages, search, metrics, conferences
  curator/        # Tag cleanup, DOI admin, data export, spam moderation
  search/         # Query analytics (ArchivedQueryHits)
```

### Settings Architecture

Settings are layered under `core/settings/`. Each file imports `from .defaults import *`.

| File | Purpose |
|------|---------|
| `defaults.py` | Base settings for all environments |
| `dev.py` | Debug toolbar, relaxed CSP |
| `test.py` | Test-specific settings |
| `e2e.py` | End-to-end test settings |
| `staging.py` | Production-like with separate DataCite prefix |
| `production.py` | Full CSP, Sentry, production DataCite |

## Patterns

### Secrets: `read_secret()`

All sensitive values come from Docker secrets mounted at `/run/secrets/`, not environment variables.

```python
# django/core/settings/defaults.py line 21
def read_secret(file, fallback=""):
    secrets_file_path = Path("/run/secrets", file)
    if secrets_file_path.is_file():
        return secrets_file_path.read_text().strip()
    else:
        return fallback

# Usage:
SECRET_KEY = read_secret("django_secret_key", os.getenv("SECRET_KEY"))
DATACITE_API_PASSWORD = read_secret("datacite_api_password")
```

### Template Configuration

Jinja2 is first in `TEMPLATES`, Django templates second (admin/allauth only):

```python
# django/core/settings/defaults.py line 560
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "APP_DIRS": True,  # discovers jinja2/ subdirs in each app
        "OPTIONS": {
            "extensions": [
                "core.jinja2ext.ViteExtension",
                "wagtail.contrib.settings.jinja2tags.settings",
                "wagtail.jinja2tags.core",
                # ...
                "csp.extensions.NoncedScript",
                "waffle.jinja.WaffleExtension",
            ],
            "environment": "core.jinja_config.environment",
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # ... used only for admin + allauth
    },
]
```

### Jinja2 Globals via `jinja_config.py`

The `environment()` function in `core/jinja_config.py` registers template globals:

```python
# Key globals available in all Jinja2 templates:
env.globals.update({
    "static": static,          # {% static "path" %}
    "url": jinja_url,          # {{ url('library:codebase-list') }}
    "markdown": markdown,      # {{ markdown(text) }}
    "to_json": to_json,        # {{ to_json(data) }}
    "constants": {             # {{ constants.DEBUG }}, {{ constants.RELEASE_VERSION }}
        "DISCOURSE_BASE_URL", "DEBUG", "RELEASE_VERSION",
        "SENTRY_DSN", "DEPLOY_ENVIRONMENT"
    },
    "format_date": format_date,
    "format_datetime": format_datetime,
    "get_download_request_metadata": get_download_request_metadata,
    # ... and more
})
```

### Middleware Stack

```python
# django/core/settings/defaults.py line 144
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",  # auto snake_case <-> camelCase
]
```

### Authentication Backends (order matters)

```python
# django/core/settings/defaults.py line 160
AUTHENTICATION_BACKENDS = (
    "allauth.account.auth_backends.AuthenticationBackend",      # 1. allauth (social + email/password)
    "core.backends.ComsesObjectPermissionBackend",              # 2. custom owner/published logic
    "guardian.backends.ObjectPermissionBackend",                 # 3. django-guardian per-object perms
)
```

### Task Queue

Huey on Redis (not Celery). Uses `DjangoRedisHuey` in `core/huey.py` to reuse the django-redis connection pool.

```python
HUEY = {
    "name": "comses",
    "huey_class": "core.huey.DjangoRedisHuey",
    "immediate": False,
}
```

### App-to-Responsibility Map

| App | Responsible For |
|-----|----------------|
| `core` | Users, MemberProfile, Events, Jobs, Platforms, SpamModeration, permissions, Discourse SSO, shared mixins, master URLconf |
| `library` | Codebases, CodebaseReleases, PeerReview, Contributors, DOI minting (DataCite), BagIt file management |
| `home` | Wagtail CMS pages, landing page, education, conferences, journals, FAQ, people, search, metrics |
| `curator` | Tag dedup/clustering, DOI admin commands, data export, spam moderation workflow, backup |
| `search` | ArchivedQueryHits for search analytics |

## Gotchas

- **Template discovery:** Jinja2 templates live in `django/<app>/jinja2/<app>/` (note the doubled app name). Django templates for admin/allauth live in `django/<app>/templates/`.
- **CamelCase middleware:** `CamelCaseMiddleWare` auto-converts between snake_case (Python) and camelCase (JS) for all JSON request/response bodies. Do NOT manually convert case in serializers.
- **`docker-compose.yml` is generated:** Never hand-edit it. Use `base.yml` + overlay files.
- **File-backed secrets:** Never put secrets in environment variables. Always use `read_secret()`. The fallback parameter exists for local dev only.
- **ACCOUNT_TEMPLATE_EXTENSION:** Set to `"jinja"` so allauth looks for `.jinja` templates, but allauth still uses the Django template backend.

## Extension

### Adding a new management command

1. Create `django/<app>/management/commands/<command_name>.py`
2. Subclass `BaseCommand`
3. Add to the appropriate app's section in the management commands table
4. Test with `docker compose exec server python manage.py <command_name>`

### Adding a new setting

1. Add default value in `django/core/settings/defaults.py`
2. Override per-environment in `dev.py`, `staging.py`, `production.py` as needed
3. If secret: use `read_secret("secret_name")` and add the file to `build/secrets/`
