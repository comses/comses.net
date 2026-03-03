---
applyTo: "**/spam*,**/moderat*"
---

## Overview

Spam detection uses a layered approach: **honeypot field** (hidden `content` field bots fill), **timing heuristic** (submissions faster than 3 seconds are flagged), and **manual moderation** via Wagtail admin. Flagged content is recorded as `SpamModeration` rows with a `GenericForeignKey` to the offending object.

## Architecture

```
django/core/
  models.py    # SpamModeration (GFK-based record), ModeratedContent (abstract mixin)
  mixins.py    # SpamCatcherSerializerMixin, SpamCatcherViewSetMixin

django/curator/
  wagtail_hooks.py  # SpamContentAdmin (Wagtail ModelAdmin), SpamContentButtonHelper
  views.py          # confirm_spam / reject_spam endpoints
```

## Patterns

### SpamModeration model (`core/models.py:135`)

Generic record that can point to any Django model via `ContentType` + `object_id`:

```python
class SpamModeration(models.Model):
    class Status(models.TextChoices):
        UNREVIEWED = "unreviewed"
        SPAM = "spam"
        NOT_SPAM = "not_spam"

    status = models.CharField(choices=Status.choices, default=Status.UNREVIEWED)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    detection_method = models.CharField(max_length=255)  # "honeypot", "form_submit_time", "manual"
    detection_details = models.JSONField(default=dict)
    reviewer = models.ForeignKey(AUTH_USER_MODEL, null=True)
```

On `.save()`, calls `update_related_object()` which sets `is_marked_spam` on the related content object.

### ModeratedContent mixin (`core/models.py:194`)

Abstract model mixed into spam-flaggable models (`Event`, `Job`, etc.):

```python
class ModeratedContent(models.Model):
    spam_moderation = models.ForeignKey(SpamModeration, null=True, on_delete=models.SET_NULL)
    is_marked_spam = models.BooleanField(default=False)  # denormalized for search indexing

    def mark_spam(self, status=SpamModeration.Status.SPAM, **kwargs): ...
    def mark_not_spam(self, user): ...

    class Meta:
        abstract = True
```

### Honeypot + timing (`core/mixins.py:191`)

`SpamCatcherSerializerMixin` injects two hidden fields into DRF serializers:

- `content` -- honeypot field (hidden in CSS). If filled, flags as spam.
- `loaded_time` -- page load timestamp. If `(now - loaded_time) < SPAM_LIKELY_SECONDS_THRESHOLD` (default: 3s), flags as spam.

```python
# In validate():
if attrs.get("content"):
    self.context["spam_context"] = self.format_spam_context("honeypot", {...})
else:
    self.check_form_submit_time(attrs)
# Fields are popped from attrs so they are not passed to model .save()
```

### ViewSet integration (`core/mixins.py:244`)

`SpamCatcherViewSetMixin` hooks into `perform_create` / `perform_update`. After the serializer saves, checks for `spam_context` in `serializer.context` and creates a `SpamModeration` record:

```python
class SpamCatcherViewSetMixin:
    def handle_spam_detection(self, serializer):
        if "spam_context" in serializer.context:
            self._validate_content_object(serializer.instance)
            self._record_spam(serializer.instance, serializer.context["spam_context"])
```

Also provides a `mark_spam` action (POST, requires `ModeratorPermissions`) for manual flagging.

### Wagtail admin review

`SpamContentAdmin` in `curator/wagtail_hooks.py` lists all `SpamModeration` records with buttons: "not spam", "mark as spam", "mark spam + deactivate user". Routes to `curator:reject_spam` and `curator:confirm_spam`.

## Gotchas

- **Content object contract:** Any model using `ModeratedContent` must also have `get_absolute_url()` and `title` attributes, or `SpamCatcherViewSetMixin._validate_content_object()` will raise `ValueError` and skip spam recording.
- **Denormalized `is_marked_spam`:** This field exists for Wagtail search indexing (cannot filter on related fields). It is updated via `SpamModeration.save()` -> `update_related_object()`. Direct DB updates to `SpamModeration` that skip `.save()` will leave this stale.
- **Serializer chaining:** If your serializer overrides `validate()`, you must call `super().validate(attrs)` to trigger spam detection. The mixin pops `content` and `loaded_time` from attrs after checking.
- **No LLM detection yet:** The secrets config includes `llm_spam_check_api_key` but LLM-based spam checking is not implemented in the codebase as of this writing.

## Extension: Adding Spam Detection to a New Model

1. Mix `ModeratedContent` into your model (adds `spam_moderation` FK + `is_marked_spam` bool)
2. Ensure your model has `get_absolute_url()` and `title` attributes
3. Mix `SpamCatcherSerializerMixin` into your DRF serializer
4. Mix `SpamCatcherViewSetMixin` into your ViewSet (before other mixins in MRO)
5. Add a migration for the new `spam_moderation` and `is_marked_spam` fields
