"""Field comparison shared by file-backed CMS draft synchronization."""


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
