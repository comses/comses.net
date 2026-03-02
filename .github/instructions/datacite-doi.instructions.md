---
applyTo: "**/datacite/**,**/doi*,**/library/doi.py"
---

# DataCite DOI Minting

CoMSES mints DataCite DOIs for peer-reviewed computational models (codebases and releases). DOIs are only minted for published, peer-reviewed `CodebaseRelease` objects and their parent `Codebase`. See `comses-overview.mdc` for general stack context.

## Architecture

| File | Purpose |
|------|---------|
| `django/library/doi.py` | `DataCiteApi` class — API client wrapper, minting, updating, logging |
| `django/library/metadata.py` | `DataCiteConverter`, `CodeMetaConverter` — model-to-metadata conversion |
| `django/library/models.py` | `DataCiteRegistrationLog`, `DataCiteAction`, `DataCiteSchema` — persistence |

## Key Patterns

### DataCiteApi

```python
from library.doi import DataCiteApi

api = DataCiteApi(dry_run=True)  # dry_run=True is the safe default
doi, success = api.mint_public_doi(codebase_or_release)
log, success = api.update_doi_metadata(codebase_or_release)
api.mint_pending_dois()  # bulk: all published peer-reviewed releases without DOIs
```

Constructor wires `DataCiteRESTClient` from the `datacite` package:
```python
self.datacite_client = DataCiteRESTClient(
    username=settings.DATACITE_API_USERNAME,
    password=settings.DATACITE_API_PASSWORD,
    prefix=settings.DATACITE_PREFIX,
    test_mode=settings.DATACITE_TEST_MODE,
)
```

### Metadata Conversion

`DataCiteConverter` in `metadata.py` converts `Codebase`/`CodebaseRelease` to DataCite schema via `codemeticulous`:

```python
from library.metadata import DataCiteConverter, CodeMetaConverter

codemeta = CodeMetaConverter.convert_release(release)       # -> CodeMeta
datacite = DataCiteConverter.convert_release(release)       # -> DataCite (codemeticulous model)
datacite = DataCiteConverter.convert_codebase(codebase)
```

Both `convert_release` and `convert_codebase` accept an optional pre-built `codemeta` arg to avoid re-computing.

### Environment Awareness

At module level in `doi.py`:
```python
IS_DEVELOPMENT = settings.DEPLOY_ENVIRONMENT.is_development
IS_STAGING     = settings.DEPLOY_ENVIRONMENT.is_staging
IS_PRODUCTION  = settings.DEPLOY_ENVIRONMENT.is_production
DATACITE_PREFIX = settings.DATACITE_PREFIX  # differs: dev/staging vs prod
```

`IS_PRODUCTION and not self.dry_run` gates real API writes in several methods. The heartbeat check skips live calls in non-production.

## Gotchas

- **`dry_run=True` by default** — `DataCiteApi.__init__` defaults to dry-run. Always pass `dry_run=False` explicitly for real minting. Every mutating method (`mint_public_doi`, `update_doi_metadata`, `_save_log_record`, `mint_pending_dois`) gates on `self.dry_run`.
- **Prefix differs by environment** — `settings.DATACITE_PREFIX` is a test prefix in dev/staging and the real CoMSES prefix in production. Never hardcode DOI prefixes.
- **Idempotent minting** — `mint_pending_dois` calls `is_valid_doi` before minting to skip already-minted objects. `update_doi_metadata` calls `is_metadata_stale` (hash comparison against latest `DataCiteRegistrationLog`) to skip no-op updates.
- **DataCite error classes** — Nine specific exception classes are imported from `datacite.errors` and mapped to HTTP status codes in `DATACITE_ERRORS_TO_STATUS_CODE`. Catch `DataCiteError` as base; inspect subclass for specific status.
  ```python
  from datacite.errors import (
      DataCiteError, DataCiteNoContentError, DataCiteBadRequestError,
      DataCiteUnauthorizedError, DataCiteForbiddenError, DataCiteNotFoundError,
      DataCiteGoneError, DataCitePreconditionError, DataCiteServerError,
  )
  ```
- **`DataCiteRESTClient` from `datacite` package** — not a custom class; it is `datacite.DataCiteRESTClient` with `schema45` for validation.
- **Metadata equivalence check** — `DataCiteApi.is_metadata_equivalent(comses_metadata, datacite_metadata)` uses `_is_deep_inclusive` for a subset/superset comparison (DataCite may return extra fields).
