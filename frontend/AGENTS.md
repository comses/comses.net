# frontend/AGENTS.md

Extends root `AGENTS.md` — read that first.

## Key Files

- `src/util.ts` — `extractDataParams()`, `parseDates()` — server-to-client data bridge
- `src/composables/api/axios.ts` — `useAxios` — base composable with CSRF injection
- `vite.config.ts` — Multi-entry auto-discovery, build output config
- `../django/core/jinja2ext.py` — `ViteExtension` — `vite_asset()` Jinja2 tag
- `../django/core/jinja_config.py` — Jinja2 environment globals (url, static, markdown, to_json)

## Conventions

1. Discrete Vue apps mount on specific DOM elements — NOT a SPA. Only the release editor uses Vue Router + Pinia.
2. `extractDataParams()` auto-converts `"True"`/`"False"` strings to booleans and JSON strings to objects. Other coercions are manual.
3. `extractDataParams()` converts camelCase param names to hyphenated `data-*` attributes: `"versionNumber"` → `data-version-number`.
4. When passing objects to `data-*` attributes from Jinja2, use `|tojson|forceescape` to prevent HTML injection. Plain strings are safe.
5. Vue components should NOT make "load initial data" API calls on mount — all bootstrap data comes via `data-*` props.
6. CSRF token comes from cookie (`csrftoken`), read by `useAxios` interceptor. Do not pass CSRF through `data-*` attributes.
7. `main.ts` is the global entry — Bootstrap CSS/JS included on every page. Do not duplicate Bootstrap imports in app entry points.
8. Vite auto-discovers entry points from `src/apps/*.ts` — drop a new `.ts` file there, no config change needed.
9. Use `{{ vite_asset("apps/<name>.ts") }}` in `{% block js %}` of Jinja2 templates to include a Vue app.
10. Only one Pinia store exists (`useReleaseEditorStore`). All other apps use local component state.
11. Prefer Bootstrap utility classes over custom CSS.
12. Multiple Vue apps can mount independently on the same page — they share no state, each reads its own `data-*` attributes.

## Architecture

The hybrid rendering pipeline: DRF ViewSet → `CommonViewSetMixin` → `RootContextHTMLRenderer` → Jinja2 template → HTML `data-*` attrs → `extractDataParams()` → Vue props. Each layer must be present.

`RootContextHTMLRenderer` injects `__all__` (full DRF response) into every Jinja2 template — use for complex serialized data in `data-*` attributes.

Build output goes to `/shared/vite/bundles` (Docker volume shared between Vite and Django containers). `manifest.json` there is what `vite_asset()` reads.

## Pitfalls

```
WRONG: onMounted(() => { api.getInitialData() })
RIGHT: All initial data comes from props via extractDataParams()

WRONG: data-config="{{ someObject }}"
RIGHT: data-config="{{ someObject|tojson|forceescape }}"

WRONG: import { useRouter } from 'vue-router'  // in non-release-editor app
RIGHT: Only the release editor uses Vue Router

WRONG: Adding a new .ts entry to rollupOptions.input manually
RIGHT: Drop the .ts file in src/apps/ — auto-discovered

WRONG: <div class="custom-flex-container"> with custom CSS
RIGHT: <div class="d-flex justify-content-between align-items-center mb-3">
```
