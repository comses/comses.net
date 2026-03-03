# AGENTS.md — django/home

CMS cluster: Wagtail pages, site-wide search, and conference management.

## Key Files

- `models.py` — All page models (`LandingPage`, `ConferencePage`, `ConferenceIndexPage`), snippets (`FaqEntry`, `Journal`, `ComsesDigest`, `ConferenceTheme`, `ConferencePresentation`, `ConferenceSubmission`)
- `../curator/wagtail_hooks.py` — All Wagtail admin registrations (`TagCleanupAdmin`, `SpamContentAdmin`)
- `views.py` — `ConferenceSubmissionView`, `SearchView`
- `management/commands/setup_conference.py` — Conference scaffold (hardcoded data, not idempotent)

## Conventions

### CMS Templates

- All CMS templates use `.jinja` extension with the Jinja2 backend. Django template tags (`{% load %}`, `{% url %}`) do not work — use Jinja2 globals from `jinja2env.py` (e.g., `{{ url('library:codebase-list') }}`).
- Use `StreamField` with `use_json_field=True` (required since Wagtail 5+).
- `wagtail_modeladmin` is used for admin hooks — do not migrate to newer `wagtail.snippets` generic views without testing.

### Page Hierarchy

- Always define `parent_page_types` and `subpage_types` on new page models — Wagtail defaults to allowing placement anywhere, which can corrupt the hierarchy.
- `CategoryIndexPage.template` is a DB field (template path stored in database). Do not expose to untrusted editors — wrong path causes 500 errors.

### Conferences

- `ConferencePage` must be a child of `ConferenceIndexPage`, which must be a child of `LandingPage`. Creating outside this hierarchy breaks `descendant_of(self)` queries.
- `ConferenceSubmissionForm` only accepts `youtube.com` and `youtu.be` video domains.
- `setup_conference` uses hardcoded user PKs — not idempotent. Fails with `MemberProfile.DoesNotExist` on databases without matching records.
- `ConferenceSubmission` and `ConferencePresentation` are separate models — no automatic promotion path.

### Site Settings

- `SiteSettings` and `SocialMediaSettings` are `BaseSiteSetting` — access via `SiteSettings.for_request(request)`, not by PK.

### Navigation

- Many pages inherit `NavigationMixin` for subnavigation/breadcrumbs via `SubNavigationLink` and `Breadcrumb` orderables — do not bypass for pages needing navigation context.

### URL Routing

- Conference URLs use `<int:slug>` (integer, year-based slugs), not `<slug:slug>`.

## Pitfalls

```
WRONG: {% url 'library:codebase-list' %}
RIGHT: {{ url('library:codebase-list') }}  # Jinja2 global

WRONG: class NewPage(Page): pass  # no parent/subpage types
RIGHT: class NewPage(Page):
           parent_page_types = ["home.ConferenceIndexPage"]
           subpage_types = []

WRONG: body = StreamField([...])
RIGHT: body = StreamField([...], use_json_field=True)

WRONG: Assuming submission == presentation
RIGHT: ConferenceSubmission and ConferencePresentation are separate models
```
