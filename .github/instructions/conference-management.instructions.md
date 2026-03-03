---
applyTo: "**/home/**"
---

## Overview

Virtual conferences are Wagtail Page types with a submission workflow. `ConferencePage` holds dates, content, and themes. Users submit presentations via `ConferenceSubmissionView`, which sends email notifications to editors. Conference page trees are scaffolded by the `setup_conference` management command.

## Architecture

```
django/home/
  models.py                           # ConferencePage, ConferenceIndexPage, ConferenceTheme,
                                      #   ConferencePresentation, ConferenceSubmission
  views.py                            # ConferenceSubmissionView (LoginRequiredMixin + CreateView)
  forms.py                            # ConferenceSubmissionForm (ModelForm)
  urls.py                             # conference/<slug>/submit/
  management/commands/setup_conference.py  # Scaffold conference pages + themes + presentations
  templates/home/conference/
    index.jinja                       # Conference detail page
    list.jinja                        # Conference index
    submission.jinja                  # Submission form
    email/notify.jinja                # Editor notification email
```

**Page tree:**

```
LandingPage (root)
  -> ConferenceIndexPage (slug: "conference")
       -> ConferencePage (per year, e.g., "comses-2018")
            -> themes (InlinePanel -> ConferenceTheme)
                 -> presentations (FK -> ConferencePresentation)
```

## Key Models

| Model | Type | Key Fields |
|-------|------|------------|
| `ConferencePage` | Wagtail Page | `start_date`, `end_date`, `submission_deadline`, `introduction` (md), `content` (md), `external_url` |
| `ConferenceIndexPage` | Wagtail Page | Lists child `ConferencePage` instances via `.conferences()` |
| `ConferenceTheme` | Snippet (ParentalKey) | `title`, `category` (Panel/Session), `description` (md), `external_url`, `page` -> ConferencePage |
| `ConferencePresentation` | Model | `title`, `external_url`, `submitter` -> MemberProfile, `contributors` M2M -> Contributor |
| `ConferenceSubmission` | Model | `title`, `abstract` (md), `video_url`, `model_url`, `submitter` -> MemberProfile, `conference` -> ConferencePage |

### Date-driven properties on `ConferencePage`

```python
is_accepting_submissions  # True if today < submission_deadline
is_open                   # True if today >= start_date
is_archived               # True if today > end_date
```

## Patterns

### Submission flow

1. User visits `conference/<slug>/submit/` (requires login via `LoginRequiredMixin`)
2. `ConferenceSubmissionView` renders form with conference context + requirements checklist
3. `ConferenceSubmissionForm` validates `video_url` (must be YouTube domain)
4. On `form_valid()`: sets `submitter` and `conference`, sends notification email to editors via Jinja2 template
5. Redirects to `conference.url` on success

### URL routing

```python
# home/urls.py
path("conference/<int:slug>/submit/", ConferenceSubmissionView.as_view(), name="submit-conference")
```

Note: `<int:slug>` -- conference pages use integer slugs (year-based).

### Setup command

`setup_conference` management command creates the `ConferenceIndexPage` under `LandingPage`, then adds `ConferencePage` children with `ConferenceTheme` entries and `ConferencePresentation` data. Contains hardcoded conference data for CoMSES 2017 and 2018.

## Gotchas

- **Wagtail page tree:** `ConferencePage` must be a child of `ConferenceIndexPage`, which must be a child of `LandingPage`. Creating pages outside this hierarchy breaks the `.conferences()` query (`descendant_of(self)`).
- **Video URL validation:** `ConferenceSubmissionForm.clean_video_url()` only accepts `youtube.com` and `youtu.be` domains. Other video hosts will be rejected.
- **`setup_conference` is not idempotent for data.** It creates themes and presentations with hardcoded user PKs. Running on a database without matching user records will fail with `MemberProfile.DoesNotExist`.
- **`ConferenceSubmission` vs `ConferencePresentation`:** These are separate models. Submissions come from the public form; presentations are curated by admins and linked to themes. There is no automatic promotion path between them.
