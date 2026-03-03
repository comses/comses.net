# django/AGENTS.md

Backend cluster detail. Root `AGENTS.md` covers commands, project structure, and global conventions — read that first.

## Key Files

- `core/settings/defaults.py` — All base settings, secret loading, TEMPLATES, REST_FRAMEWORK, WAGTAILSEARCH_BACKENDS
- `core/mixins.py` — `CommonViewSetMixin`, `HtmlListModelMixin`, `HtmlRetrieveModelMixin`, `SpamCatcherSerializerMixin`, `SpamCatcherViewSetMixin`
- `core/backends.py` — `ComsesObjectPermissionBackend`, `add_to_comses_permission_whitelist()`, `HANDLED_MODELS`
- `core/tests/permissions_base.py` — `BaseViewSetTestCase`, `ResponseStatusCodesMixin`, `ApiAccountMixin`
- `core/tests/base.py` — `UserFactory`, `ContentModelFactory`, `BaseModelTestCase`

## Conventions

### General

- Follow PEP 8, use type hints
- Models are fat; features spanning many models go in separate modules (e.g., `library/fs.py`, `home/metrics.py`)
- Generate migrations (`manage.py makemigrations [app]`), never hand-write them
- Huey tasks are defined and discovered in `tasks.py` modules within each app; consumer runs as a separate process — must be reloaded for changes to tasks or their dependencies

### DRF / API

- HTML is the default renderer (`RootContextHTMLRenderer` listed first). API clients must send `Accept: application/json`.
- `context_object_name` and `context_list_name` control Jinja2 template variable names.
- Custom `@action` decorators must add to `ALLOWED_ACTIONS` or override `get_template_names()` — default raises `NotFound` for unhandled actions.
- `SmallResultSetPagination` caps at `max_result_window=2500` — Elasticsearch refuses beyond this offset.

### Permissions

- Three-layer auth: allauth → `ComsesObjectPermissionBackend` (owner/published) → django-guardian (per-object). Order matters.
- `obj.live == True` grants anonymous view access, checked before guardian.
- Non-deletable objects (`obj.deletable is False`) raise `PermissionDenied` regardless of user.
- `ObjectPermissions` allows unauthenticated GET. Use `ViewRestrictedObjectPermissions` for restricted viewing.

### Testing

- No pytest, no factory_boy — use `manage.py test` with custom factories in `core/tests/base.py`.
- `check_list()` calls `update_index` — tests need Elasticsearch running via Docker.
- E2E uses Borg restore (`make e2e`), not fixtures.
- Use `data-cy` attributes for Cypress selectors, not CSS classes or IDs.

### Spam

- `SpamCatcherSerializerMixin` pops `content` and `loaded_time` after checking — always call `super().validate(attrs)` in serializer overrides.
- Models with `ModeratedContent` must have `get_absolute_url()` and `title`, or spam recording silently fails.
- `is_marked_spam` is denormalized for Wagtail search — direct DB updates that skip `.save()` leave it stale.

### Elasticsearch

- `AUTO_UPDATE: True` means every `.save()` hits ES. Use `manage.py update_index` for bulk ops.
- `RelatedFields` updates are not automatic — save the parent or run `update_index` after changing related models.
- Index rebuild required after `search_fields` changes.

### Discourse SSO

- `sanitize_username()` can produce collisions — mitigated by `shortuuid` but not eliminated.
- User creation signal fires before email verification — Discourse user may exist before Django confirmation.

### Invoke Tasks

- AI agents must NEVER execute invoke tasks. Ask the human to run them.
- Tasks assume Django + PostgreSQL inside the container — running on host fails.

## Pitfalls

```
WRONG: Convert camelCase manually in a DRF serializer
RIGHT: Let CamelCaseMiddleWare handle it automatically

WRONG: @add_to_comses_permission_whitelist omitted on new model
RIGHT: Always decorate permission-controlled models

WRONG: pytest.mark.django_db + conftest.py
RIGHT: class MyTest(BaseViewSetTestCase): with manage.py test

WRONG: Override validate() without calling super()
RIGHT: Always call super().validate(attrs) to trigger spam detection

WRONG: secrets via env var: os.environ["DB_URL"]
RIGHT: secrets via file: read_secret("db_password")
```
