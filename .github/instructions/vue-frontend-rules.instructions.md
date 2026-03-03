---
applyTo: "**/frontend/**"
---

# Vue Frontend Rules

## Overview

The frontend uses Vue 3 Composition API + TypeScript + Bootstrap 5. It is NOT a single-page application -- discrete Vue apps mount onto specific DOM elements in Django-rendered Jinja2 pages. The only exception is the release editor, which is a full SPA with Vue Router + Pinia. See `comses-overview.mdc` for stack context and `django-vue-hybrid-rendering.mdc` for the server/client bridge pattern.

## Architecture

```
frontend/
  src/
    apps/              # Entry points (one per page/feature)
    components/        # Vue components
      form/            # Form field components (TextField, MarkdownField, TaggerField, etc.)
      releaseEditor/   # Release editor SPA components
    composables/       # Vue composables
      api/             # API layer (useAxios base + domain composables)
      form.ts          # useField() composable for form context
    stores/            # Pinia stores (releaseEditor only)
    types.ts           # TypeScript interfaces
    util.ts            # extractDataParams(), parseDates()
    scss/              # Bootstrap theme + custom styles
  vite.config.ts       # Multi-entry Vite config
  package.json
```

### Build System

Vite 4 with auto-discovered multi-entry build:

```typescript
// frontend/vite.config.ts
const getAppEntries = () => {
  const appsDir = resolvePath("./src/apps");
  const entries: { [key: string]: string } = {};
  fs.readdirSync(appsDir).forEach(file => {
    if (file.endsWith(".ts")) {
      const name = file.replace(".ts", "");
      entries[name] = resolvePath(`./src/apps/${file}`);
    }
  });
  return entries;
};

export default defineConfig({
  build: {
    outDir: "/shared/vite/bundles",
    manifest: true,                   // django-vite reads manifest.json
    rollupOptions: { input: getAppEntries() },
  },
  // Dev: HMR on localhost:5173
  // Prod: one-shot build to /shared/vite/bundles
});
```

Every `.ts` file in `src/apps/` becomes a separate Rollup entry point. Django includes them via the `{{ vite_asset("apps/<name>.ts") }}` Jinja2 tag.

### App Entry Points

| App | Mounts On | Description |
|-----|-----------|-------------|
| `main.ts` | (global) | CSS + Bootstrap JS on every page |
| `codebase_edit.ts` | `#codebase-form` | Codebase creation/edit form |
| `codebase_list.ts` | `#sidebar`, `#sortby` | Model library filter sidebar + sort |
| `release_editor.ts` | `#release-editor` | Full SPA: Pinia + Vue Router for multi-step release editing |
| `event_calendar.ts` | `#event-calendar` | FullCalendar month/week/list view |
| `event_edit.ts` | `#event-form` | Event create/edit form |
| `event_list.ts` | `#sidebar`, `#sortby` | Event listing filters |
| `job_edit.ts` | `#job-form` | Job posting create/edit form |
| `job_list.ts` | `#sidebar`, `#sortby` | Job listing filters |
| `metrics.ts` | `#metrics-view` | Highcharts metrics dashboard |
| `profile_edit.ts` | `#profile-form` | User profile edit form |
| `profile_list.ts` | `#sidebar` | Member listing filter sidebar |
| `image_gallery.ts` | `#image-gallery` | Image gallery carousel |
| `release_download.ts` | `#download-form` | Download survey modal |
| `release_regenerate_share_uuid.ts` | `#regenerate-share-uuid` | Private share URL regeneration |
| `review_editor.ts` | `#review-editor` | Peer review management |
| `reviewer_list.ts` | `#reviewer-list` | Admin reviewer management |

## Patterns

### App Entry Point Pattern

Every app follows the same pattern:

```typescript
// frontend/src/apps/codebase_edit.ts
import "vite/modulepreload-polyfill";
import { createApp } from "vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("codebase-form", ["identifier"]);
createApp(CodebaseEditForm, props).mount("#codebase-form");
```

### API Composables

All API composables are built on `useAxios` (in `composables/api/axios.ts`):

```typescript
// composables/api/axios.ts
export function useAxios(baseUrl?: string, config?: AxiosRequestConfig) {
  // Creates axios instance with CSRF token injection
  // Returns: { instance, state, get, post, postForm, put, del, detailUrl, searchUrl }
}
```

CSRF token is read from the `csrftoken` cookie automatically via interceptor.

| Composable | File | Base URL | Purpose |
|------------|------|----------|---------|
| `useAxios` | `api/axios.ts` | (configurable) | Base composable with CSRF, error parsing |
| `useCodebaseAPI` | `api/codebase.ts` | `/codebases/` | Codebase CRUD + media |
| `useReleaseEditorAPI` | `api/releaseEditor.ts` | `/codebases/` | Release CRUD + file upload + publish |
| `useEventAPI` | `api/event.ts` | `/events/` | Event CRUD + calendar |
| `useJobAPI` | `api/job.ts` | `/jobs/` | Job CRUD |
| `useProfileAPI` | `api/profile.ts` | `/users/` | Profile search + update + avatar |
| `useContributorAPI` | `api/contributor.ts` | `/contributors/` | Contributor search |
| `useReviewEditorAPI` | `api/reviewEditor.ts` | `/reviews/` | Review management |
| `useTagsAPI` | `api/tags.ts` | `/tags/` | Tag autocomplete |
| `useRORAPI` | `api/ror.ts` | `api.ror.org/v2` | External ROR organization search |

### State Management

Only one Pinia store exists: `useReleaseEditorStore` in `stores/`. It manages release files, metadata, and contributor state for the multi-step release editor SPA. All other apps are simple enough to use local component state.

### Component Library

**Form fields** (`components/form/`): TextField, TextareaField, MarkdownField, SelectField, MultiSelectField, CheckboxField, DatepickerField, TaggerField, ResearchOrgField, ResearchOrgListField, TextListField, HoneypotField. All registered via `useField()` composable with parent form context.

**Reusable UI**: BootstrapModal, BootstrapTooltip, ListSidebar, ListSortBy, ImageGallery.

**Release Editor** (`components/releaseEditor/`): Multi-step workflow with Vue Router -- UploadFormPage, MetadataFormPage, ContributorsPage. Includes drag-and-drop contributor ordering, file upload with progress, BagIt preview tree, publish/review modals.

### Styling

- Bootstrap 5.2.3 with custom theme variables
- Primary: `#92c02e` (green), Secondary: `#22b1e6` (blue)
- Custom font: "Alte-DIN-1451-Mittelschrift" for codebase titles
- Base font: Open Sans (Google Fonts)
- Font Awesome 5 icons
- Prefer Bootstrap utility classes over custom CSS

```
// CORRECT
<div class="d-flex justify-content-between align-items-center mb-3">

// AVOID
<div class="custom-flex-container">  /* with custom CSS */
```

### Path Aliases

```typescript
// vite.config.ts resolve.alias
"@" -> "./src"      // import Foo from "@/components/Foo.vue"
"~" -> "./node_modules"
```

## Gotchas

- **NOT React, NOT Tailwind.** This is Vue 3 + Bootstrap 5. Do not introduce React components or Tailwind classes.
- **`extractDataParams()` converts `data-*` attributes.** It auto-converts camelCase param names to hyphenated `data-` attributes. `"identifier"` looks for `data-identifier`, `"versionNumber"` looks for `data-version-number`.
- **Python booleans in templates.** `extractDataParams()` handles `"True"` and `"False"` strings from Django templates, converting them to JS booleans.
- **Only the release editor uses Vue Router.** All other apps are simple mount-and-render components. Do not add Vue Router to non-release-editor apps.
- **CSRF from cookie, not from template.** The `csrftoken` cookie is read by the axios interceptor in `useAxios`. There is no need to pass CSRF tokens via data attributes.
- **`vite_asset()` tag in templates.** To include a Vue app on a page, use `{{ vite_asset("apps/<name>.ts") }}` in the `{% block js %}` of the Jinja2 template.
- **`main.ts` is global.** It includes Bootstrap CSS/JS on every page. Do not duplicate Bootstrap imports in individual app entry points.

## Extension

### Adding a new Vue app

1. Create `frontend/src/apps/<name>.ts` with the entry point pattern (import, extractDataParams, createApp, mount)
2. Create the root Vue component in `frontend/src/components/`
3. Add the mount point `<div id="<mount-id>" data-...>` in the Jinja2 template
4. Include `{{ vite_asset("apps/<name>.ts") }}` in `{% block js %}`
5. Vite auto-discovers the new entry -- no config change needed

### Adding a new API composable

1. Create `frontend/src/composables/api/<name>.ts`
2. Import and use `useAxios` from `./axios`
3. Export a composable function following the `use<Name>API` naming convention
4. Add to the composables index at `frontend/src/composables/api/index.ts`
