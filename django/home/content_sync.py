"""Shared revision handling for file-backed CMS content."""


def update_fields(instance, values):
    """Update source-managed fields in memory, comparing Markdown as raw text."""
    changed = False
    for name, value in values.items():
        current = getattr(instance, name)
        is_markup = hasattr(current, "raw")
        current = getattr(current, "raw", current)
        if current != value:
            setattr(instance, name, value)
            if is_markup:
                # Wagtail serializes revisions without saving body fields. Render
                # in memory so preview HTML matches the new source, without
                # writing draft content to the live page.
                instance._meta.get_field(name).pre_save(instance, add=instance._state.adding)
            changed = True
    return changed


def save_source_revision(page, *, changed, publish_initial):
    """Publish first versions by default, leaving later source changes in drafts."""
    initial = publish_initial and not page.live and page.first_published_at is None and page.live_revision_id is None
    if not changed and not initial:
        return None, False
    revision = page.save_revision() if changed else page.get_latest_revision()
    if revision is None:
        revision = page.save_revision()
    if initial:
        revision.publish()
    return revision, initial
