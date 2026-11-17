# DRF content negotiation audit

Date: 2026-11-14

The programming language error is caused by an API endpoint inheriting the global HTML renderer. The query succeeds; rendering then requests a nonexistent template. The remediation makes JSON the global default and enables HTML only for declared actions on mixed page and API viewsets.

The baseline route inventory contains 100 registered route and method combinations, including 12 supplied by Wagtail and drf-spectacular, plus the nested `_change_peer_review_status` API called by `PeerReviewEditorView.put`. Beyond programming languages, 62 other application route and method combinations could select HTML without a valid success response template. These are baseline configuration findings, not 62 observed production incidents. There are 19 GET operations and 43 write operations in this group.

## Findings

| View | Affected actions | Failure during HTML rendering |
| --- | --- | --- |
| `core.views.EventViewSet` | `create`, `update`, `partial_update`, `destroy` | NotFound |
| `core.views.JobViewSet` | `create`, `update`, `partial_update`, `destroy` | NotFound |
| `core.views.MemberProfileImageUploadView` | `post` | ImproperlyConfigured |
| `core.views.MemberProfileViewSet` | `create`, `update`, `partial_update` | NotFound |
| `core.views.TagListView` | `list` | ImproperlyConfigured |
| `core.views.ToggleFollowUser` | `post` | ImproperlyConfigured |
| `library.views.CodebaseGitRemoteViewSet` | `active_remote`, `build_local_repo`, `disconnect_remote`, `github_releases`, `import_github_release`, `local_releases`, `push_all`, `setup_user_github_remote`, `submitter_installation_status`, `retrieve`, `update`, `partial_update` | ImproperlyConfigured |
| `library.views.CodebaseImageViewSet` | `list`, `create`, `clear`, `destroy` | ImproperlyConfigured |
| `library.views.CodebaseReleaseFilesOriginalsViewSet` | `list`, `create`, `clear_category`, `destroy` | ImproperlyConfigured |
| `library.views.CodebaseReleaseFilesSipViewSet` | `list`, `update_category` | ImproperlyConfigured |
| `library.views.CodebaseReleaseViewSet` | `create`, `update`, `partial_update`, `contributors`, `publish`, `regenerate_share_uuid`, `request_download` | NotFound |
| `library.views.CodebaseViewSet` | `create`, `github_installation_status`, `submitted_codebases`, `update`, `partial_update` | NotFound |
| `library.views.ContributorList` | `get` | ImproperlyConfigured |
| `library.views.PeerReviewFeedbackViewSet` | `list`, `retrieve` | ImproperlyConfigured |
| `library.views.PeerReviewInvitationViewSet` | `list`, `send_invitation`, `retrieve`, `resend_invitation` | ImproperlyConfigured |
| `library.views.PeerReviewerViewSet` | `list`, `create`, `retrieve`, `update`, `partial_update` | NotFound, TemplateDoesNotExist |
| `library.views._change_peer_review_status` | `_change_peer_review_status` | ImproperlyConfigured |
| `library.views.list_review_event_log` | `get` | ImproperlyConfigured |

`CommonViewSetMixin.get_template_names()` raises DRF `NotFound` for actions other than list, retrieve, and delete. This happens during deferred response rendering, after DRF dispatch has completed, so the normal DRF exception handler cannot turn it into an API error response. Viewsets without any template configuration instead raise `ImproperlyConfigured`. Reviewer list and detail actions request nonexistent templates, like programming languages.

Write actions are the highest priority. Examples include publishing, generating a share UUID, importing or pushing Git repositories, sending review invitations, uploading files, and following a user. Database writes, queued tasks, file operations, or email can succeed before rendering fails. Method-level transaction decorators exit before deferred rendering; they do not make a render failure undo those effects. A client retry can therefore repeat an operation.

## Intentional HTML responses

The following operations have a valid HTML path and must retain it during remediation:

- Member profiles, events, and jobs: list and detail templates.
- Events calendar: an explicit response template or a redirect when browser query parameters are present.
- Codebases: the list template and detail redirect to the latest accessible release.
- Git remotes: the list action supplies `library/codebases/git.jinja` explicitly. Its detail, update, and custom API actions do not supply templates.
- Releases: the list redirect, detail template, download response, and browser redirects for requesting peer review and notifying reviewers.
- Shared releases: the detail template and review archive download.
- Spam moderation actions: explicit redirects.

Twelve Wagtail admin and schema operations use dependency-provided renderers or templates. They do not exhibit this inherited custom HTML renderer problem; their internal behavior was outside this audit.

## Additional coverage

HEAD follows the corresponding GET action and inherits its result. Automatic OPTIONS was also exposed: views inheriting the HTML renderer had no metadata template. The shared policy now selects JSON for metadata requests, including on viewsets whose GET actions serve pages.

`FeaturedContentListAPIView` is defined but has no route reference in the checkout. It now inherits the JSON default if connected later. The development-only codebase delete view is omitted by the test environment URL configuration and inherits the production codebase view policy.

The event calendar previously compared `request.accepted_media_type` directly with `application/json`, so a parameterized JSON media type could miss that branch. It now checks `request.accepted_renderer.format == "json"`.

## Standardization options

| Approach | Benefit | Tradeoff |
| --- | --- | --- |
| JSON globally, explicit HTML support per action | New APIs are safe by default; OPTIONS can stay JSON | Requires migrating existing page views and preserving browser redirects deliberately |
| Explicit JSON base views with the current global default | Smaller rollout; follows the current download preview fix | Unconverted and newly added endpoints can still inherit HTML accidentally |
| Route-wide CI contract or Django system check | Detects forgotten declarations and missing declared templates before deployment | Requires explicit declarations for response templates, redirects, files, and dynamic template choices |
| HTML renderer falls back to JSON when templates fail | Reduces visible errors centrally | Hides broken pages, makes response types depend on template installation, and can expose an unintended serialized response |

The implemented policy makes JSON the default and requires an explicit set of HTML actions on mixed page and API viewsets. It reuses the camel-case renderer to preserve response field names. A route-wide contract test rejects undeclared HTML actions and verifies declared templates exist. Functional request tests also cover page rendering, browser redirects, and files: template existence alone cannot establish correct rendering.

Changing renderer order to JSON first is insufficient: an explicit `Accept: text/html` still selects HTML when that renderer remains available. JSON-only endpoints should return 406 for HTML-only requests; normal browser headers with a wildcard fallback can receive JSON. Do not ignore Accept headers in a custom negotiator to force a successful response.

## Implemented renderer policy

`REST_FRAMEWORK.DEFAULT_RENDERER_CLASSES` contains only `CamelCaseJSONRenderer`. API-only views need no local renderer override, including programming languages and download previews.

Mixed viewsets explicitly inherit `HtmlActionRendererMixin` and declare `html_actions`. The mixin preserves HTML-first negotiation for those actions and removes HTML from every other action before content negotiation. New API actions and OPTIONS therefore use JSON automatically. Its class-level renderer declaration preserves DRF's `Vary: Accept` header for pages that also support JSON.

The HTML declarations preserve the page, redirect, and download operations listed above. Permission checks remain in the existing handlers and permission classes. HTML-only requests to API actions receive 406 before the handler runs. Browser requests that accept a wildcard fallback can receive JSON.

`core.tests.test_content_negotiation` enumerates application DRF routes and the nested review-status API. It checks absent, wildcard, browser, explicit JSON, and HTML-only Accept headers, including HEAD and OPTIONS. It renders synthetic successful JSON responses without executing business handlers and checks declared page templates separately. Further tests cover actual page rendering, parameterized calendar JSON requests, and rejection before write handlers run.

Retry safety and idempotency remain separate work: this policy prevents template rendering failures after successful writes but does not deduplicate retried commands or background tasks.

## Validation and limits

The audit ran route enumeration and template lookup inside the existing application image with no dependency services started. Source review distinguished explicit response templates, redirects, and file responses from template lookup failures. The exact original programming language exception was reproduced by temporarily restoring inherited renderer settings in the disposable process. Ten list and detail cases then verified the fixed behavior across absent, wildcard, JSON, browser, and HTML-only Accept headers, with database connections explicitly blocked.

The repository-standard tests ran in a separate Compose project under `/tmp` with fresh PostgreSQL, Redis, Elasticsearch, and shared storage. The existing local database and file storage were not mounted in that project. Verification covered 107 distinct tests: eight renderer-policy tests and 99 core/library view tests.

Commands executed from that disposable project:

```bash
make test TEST_ARGS=core.tests.test_content_negotiation
make test TEST_ARGS='core.tests.test_views library.tests.test_views'
make test TEST_ARGS='core.tests.test_content_negotiation library.tests.test_views.CodebaseRenderPageTestCase library.tests.test_views.CodebaseReleaseRenderPageTestCase'
```

The broad view run passed 97 of 98 cases. After correcting a new assertion about DRF's empty-response headers, the final focused run passed all 13 cases, including the corrected GitHub test, browser downloads, and route-wide checks. No production-code changes were needed after the broad run.

The new test module passes Ruff lint and formatting checks, and the diff passes whitespace checks. No migrations are required.

The findings table records the baseline exposures. The route-wide tests enumerate the current application endpoints and enforce the implemented policy.
