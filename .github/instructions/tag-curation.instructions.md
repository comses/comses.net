---
applyTo: "**/tag*/**,**/curator/**"
---

## Overview

Tag curation lives in `django/curator/`. It provides two workflows: **manual tag cleanup** (rename/merge/delete tags via Wagtail admin) and **ML-powered clustering** (dedupe library groups similar tags into canonical mappings). All tag operations go through `TagMigrator` which rewrites M2M through-model references before deleting old tags.

## Architecture

```
django/curator/
  models.py              # TagCuratorProxy, TagCleanup, TagCleanupTransaction, TagMigrator,
                         #   TagCluster, CanonicalTag, CanonicalTagMapping
  tag_deduplication.py   # AbstractTagDeduper, TagClusterer (dedupe lib), TagClusterManager
  wagtail_hooks.py       # TagCleanupAdmin, SpamContentAdmin (Wagtail ModelAdmin)
  management/commands/
    curator_cluster_tags  # ML clustering pipeline
    curator_clean_tags    # Interactive tag cleanup staging
```

**Key Models:**

| Model | Purpose |
|-------|---------|
| `TagCuratorProxy` | Proxy over `taggit.Tag` with query helpers (`with_comma`, `programming_languages`, `platforms`, `with_uppercase`) |
| `TagCleanup` | Staged rename: `old_name` -> `new_name`, linked to `TagCleanupTransaction` after processing |
| `TagCleanupTransaction` | Batch record of applied cleanup operations (has `date_created`) |
| `TagMigrator` | Service class: discovers through tables, creates new tags, copies through-model refs, deletes old tag |
| `TagCluster` | ML output: `canonical_tag_name` + M2M to `Tag` + `confidence_score` |
| `CanonicalTag` | Deduplicated tag identity (`name`, unique) |
| `CanonicalTagMapping` | Maps `Tag` (OneToOne, PK) -> `CanonicalTag` with curator + confidence |

## Patterns

### Through-table discovery

`get_through_tables()` in `models.py` auto-discovers all M2M relationships to `taggit.Tag` by filtering `Tag._meta.related_objects` for `ManyToOneRel` where the related model has a `ParentalKey` named `content_object`:

```python
def get_through_tables():
    return [
        m.related_model
        for m in Tag._meta.related_objects
        if isinstance(m, models.ManyToOneRel)
        and has_parental_object_content_field(m.related_model)
    ]
```

### Tag migration flow

```python
# TagCleanupQuerySet.process() -- runs inside @transaction.atomic
migrator = TagMigrator()
migrator.migrate(old_name="netlogo 6.0", new_names=["NetLogo"])
# 1. Creates "NetLogo" tag if it doesn't exist
# 2. For each through-model: copies refs from old tag to new tags (bulk_create)
# 3. Deletes old tag
# 4. Creates TagCleanupTransaction, links processed TagCleanup rows
```

### ML clustering (dedupe library)

```python
# tag_deduplication.py
class TagClusterer(AbstractTagDeduper):
    def __init__(self, clustering_threshold):
        self.deduper = dedupe.Dedupe(AbstractTagDeduper.FIELDS)  # FIELDS = [String("name")]
        self.prepare_training()  # loads from curator/clustering_training.json if exists

    def cluster_tags(self):
        self.deduper.train()
        return self.deduper.partition(self.prepare_training_data(), self.clustering_threshold)
```

Training data persists to `curator/clustering_training.json`. Clusters are saved as `TagCluster` rows, then reviewed via `TagClusterManager.console_label()` or Wagtail admin before being promoted to `CanonicalTagMapping`.

### Wagtail admin

`TagCleanupAdmin` is registered via `modeladmin_register(TagCleanupAdmin)` in `wagtail_hooks.py`. Provides buttons for: Migrate Pending Changes, Delete All Active, Porter Stemmer grouping, Platform/Language grouping. Uses custom `TagCleanupButtonHelper` with actions routed to `curator:process_tagcleanups`.

## Gotchas

- **Transaction safety:** `TagCleanupQuerySet.process()` is wrapped in `@transaction.atomic`. If you add new migration logic, keep it inside this boundary or you risk orphaned through-model refs.
- **ParentalKey requirement:** `get_through_tables()` only finds through models using Wagtail's `ParentalKey` for `content_object`. Standard Django ForeignKey through models will be invisible.
- **Slug uniqueness:** `TagMigrator.create_new_tags()` saves tags one-by-one (not `bulk_create`) because `taggit.Tag` auto-generates unique slugs that require sequential saves.
- **NLTK dependency:** `TagCleanup.find_groups_by_porter_stemmer()` requires NLTK data (stopwords, punkt tokenizer). These must be downloaded in the Docker image.

## Extension: Adding a New Tag Cleanup Operation

1. Add a class method on `TagCleanup` that returns a list of `TagCleanup(new_name=..., old_name=...)` instances (see `find_groups_by_porter_stemmer` and `find_groups_by_platform_and_language` as examples)
2. Add a new entry to `TagCleanupAction` enum in `wagtail_hooks.py`
3. Add a corresponding button method on `TagCleanupButtonHelper`
4. Handle the new action in `curator/views.py` process view
5. The actual migration is automatic -- `TagCleanupQuerySet.process()` handles all pending `TagCleanup` rows regardless of origin
