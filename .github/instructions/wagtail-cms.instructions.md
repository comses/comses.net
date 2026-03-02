---
applyTo: "**/home/**,**/*page*.py"
---

# Wagtail CMS — Page Models, Snippets & Admin

## Overview

Wagtail 6 powers the CMS pages for the public website. All public-facing
content pages — landing page, education resources, conferences, FAQ, team
directory, journals, and newsletter digests — are managed through Wagtail's
page tree and snippet system.

## Architecture

All page models live in `django/home/models.py`. Admin hooks are registered in
`django/curator/wagtail_hooks.py`.

### Page Types

| Class | Template | Purpose |
|---|---|---|
| `LandingPage` | `home/index.jinja` | Homepage: featured content, forum activity, jobs, events |
| `CategoryIndexPage` | `home/category_index.jinja` (configurable) | Section index with callout cards and subnavigation |
| `EducationPage` | `home/education.jinja` | Tutorial cards grouped by category with tag filtering |
| `TutorialDetailPage` | `home/tutorial.jinja` | Individual tutorial with Markdown body |
| `StreamPage` | `home/stream_page.jinja` | Generic StreamField page (heading, paragraph, image, url blocks) |
| `MarkdownPage` | `home/markdown_page.jinja` | Generic Markdown page with optional jumbotron header |
| `ConferencePage` | `home/conference/index.jinja` | Conference with dates, themes, submissions, Discourse link |
| `ConferenceIndexPage` | `home/conference/list.jinja` | Lists all child ConferencePages |
| `FaqPage` | `home/about/faq.jinja` | Renders all `FaqEntry` snippets by category |
| `PeoplePage` | `home/about/people.jinja` | Team directory from `PeopleEntryPlacement` snippets |
| `JournalIndexPage` | `home/resources/journals.jinja` | Lists `Journal` snippets via placements |
| `PlatformIndexPage` | `home/resources/frameworks.jinja` | Lists `Platform` snippets via placements |
| `ContactPage` | `home/about/contact.jinja` | Contact form with POST handler |
| `NewsIndexPage` / `NewsPage` | — | News section (legacy; NewsPage enforces `parent_page_types`) |

### Snippets (registered with `@register_snippet`)

| Class | Purpose |
|---|---|
| `ComsesDigest` | Newsletter digest archive (season, volume, static PDF path, DOI) |
| `FaqEntry` | Individual FAQ item with category, question, Markdown answer |
| `PeopleEntryPlacement` | Maps a `MemberProfile` to `PeoplePage` with category and term |
| `Journal` | Academic journal with name, URL, ISSN, Markdown description, tags |
| `ConferenceTheme` | Panel/session under a `ConferencePage` with linked presentations |

### Site-Wide Settings

`SiteSettings` and `SocialMediaSettings` are Wagtail `BaseSiteSetting` models.
Access them in views and templates via:

```python
from wagtail.contrib.settings.context_processors import SettingsContextProcessor
# or directly:
SiteSettings.for_request(request)
```

## Patterns

### `content_panels` Configuration

Every page model defines `content_panels` extending `Page.content_panels`:

```python
class MyPage(Page):
    body = MarkdownField()

    content_panels = Page.content_panels + [
        FieldPanel("body"),
        InlinePanel("related_items", label="Related Items"),
    ]
```

### StreamField Usage

`StreamPage` uses a `StreamField` with `use_json_field=True` (required in
Wagtail 5+). Block types available: `CharBlock`, `RichTextBlock`,
`ImageChooserBlock`, `URLBlock`.

```python
body = StreamField([
    ("heading", blocks.CharBlock(classname="full title")),
    ("paragraph", blocks.RichTextBlock()),
    ("image", ImageChooserBlock()),
    ("url", blocks.URLBlock(required=False)),
], use_json_field=True)
```

### Snippet Placement Pattern

Snippets are linked to pages via explicit placement models using `ParentalKey`:

```python
class JournalSnippetPlacement(models.Model):
    page = ParentalKey("home.JournalIndexPage", related_name="journal_placements")
    journal = models.ForeignKey(Journal, related_name="+", on_delete=models.CASCADE)
```

### NavigationMixin

Many pages inherit `NavigationMixin` (alongside `Page`) for subnavigation and
breadcrumb support via `SubNavigationLink` and `Breadcrumb` orderable models.

### Admin Hooks (`curator/wagtail_hooks.py`)

`wagtail_modeladmin` is used (not the newer `wagtail.snippets` generic views)
for `TagCleanup` and `SpamModeration`. A `construct_homepage_panels` hook adds
`RecentActivityPanel` to the Wagtail admin dashboard showing recent signups,
releases, events, and jobs.

## Gotchas

1. **Jinja2 templates, not Django templates.** All page templates use `.jinja`
   extensions and are rendered by the Jinja2 backend. Django template tags
   (`{% load %}`, `{% url %}`) do not work — use Jinja2 syntax and registered
   globals/filters from `django/home/jinja2env.py`.

2. **Page tree hierarchy is enforced.** `NewsPage` sets
   `parent_page_types = ["home.NewsIndexPage"]` — Wagtail will refuse to place
   it elsewhere. When adding new page types, define `parent_page_types` and
   `subpage_types` explicitly or Wagtail defaults to allowing anything anywhere.

3. **`CategoryIndexPage.template` is a DB field.** The template path is stored
   in the database (not hardcoded), allowing per-instance overrides. Don't
   expose this to untrusted editors — wrong paths cause 500 errors.

## Adding a New Page Type

1. Define the model class in `django/home/models.py`, inheriting from `Page`
   (and optionally `NavigationMixin`).
2. Add `content_panels = Page.content_panels + [...]` with `FieldPanel` /
   `InlinePanel` entries for all editable fields.
3. Set `parent_page_types` and `subpage_types` to constrain placement in the
   page tree.
4. Create the Jinja2 template at the path declared in `template` (use
   `home/<name>.jinja` convention).
5. Generate and apply migrations: `python manage.py makemigrations home &&
   python manage.py migrate`.
6. Register any related orderable child models with `ParentalKey` pointing to
   the new page and expose them via `InlinePanel` in `content_panels`.

## Cross-References

- See `comses-overview.mdc` for the full application map and Django app layout.
- See `django-backend-rules.mdc` for model conventions (MarkdownField, signals).
- See `django-vue-hybrid-rendering.mdc` for how Jinja2 templates integrate with
  Vue components on the same page.
