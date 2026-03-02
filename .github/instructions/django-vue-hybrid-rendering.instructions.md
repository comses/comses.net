---
applyTo: "**/templates/**,**/frontend/src/**"
---

# Django/Vue Hybrid Rendering

## Overview

CoMSES Net uses a hybrid rendering pattern where Django serves complete HTML pages via Jinja2 templates, and Vue 3 apps mount onto specific DOM elements for interactivity. Data flows from server to client through HTML `data-*` attributes parsed by `extractDataParams()`. The only exception is the release editor, which is a full SPA.

## Architecture

### The Full Request-to-Render Flow

```
1. HTTP Request (browser)
       |
2. DRF ViewSet (e.g., CodebaseViewSet)
       |
3. CommonViewSetMixin.get_template_names()
       |  -> resolves to e.g. "library/codebases/edit.jinja"
       |
4. HtmlRetrieveModelMixin.retrieve()
       |  -> if HTML: returns Response({context_object_name: instance})
       |  -> if JSON: returns Response(serializer.data)
       |
5. RootContextHTMLRenderer.render()
       |  -> adds context["__all__"] = data
       |  -> renders Jinja2 template with context
       |
6. Jinja2 Template (e.g., library/codebases/edit.jinja)
       |  -> renders HTML with <div id="mount-id" data-key="value">
       |  -> includes {{ vite_asset("apps/codebase_edit.ts") }}
       |
7. Browser receives HTML, loads JS bundle
       |
8. Vue app entry (e.g., apps/codebase_edit.ts)
       |  -> extractDataParams("mount-id", ["key"]) reads data-* attributes
       |  -> createApp(Component, props).mount("#mount-id")
       |
9. Vue component renders inside the <div>, makes API calls for dynamic data
```

## Patterns

### Concrete Example: Codebase Edit

**Step 1: Jinja2 Template** (`django/library/jinja2/library/codebases/edit.jinja`)

```html
{% extends "base.jinja" %}

{% block content %}
{% include "library/includes/publish_model_help.jinja" %}
<p>Publishing the software that your research depends on...</p>
<div id="codebase-form" {% if object %} data-identifier="{{ object.identifier }}" {% endif %}></div>
{% endblock %}

{% block js %}
{{ vite_asset("apps/codebase_edit.ts") }}
{% endblock %}
```

Key points:
- `data-identifier="{{ object.identifier }}"` passes the codebase identifier from server to client
- `object` is the model instance provided by `HtmlRetrieveModelMixin` via `context_object_name`
- `{{ vite_asset(...) }}` loads the JS bundle (hashed filename in prod via `manifest.json`)

**Step 2: Vue Entry Point** (`frontend/src/apps/codebase_edit.ts`)

```typescript
import "vite/modulepreload-polyfill";
import { createApp } from "vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("codebase-form", ["identifier"]);
createApp(CodebaseEditForm, props).mount("#codebase-form");
```

**Step 3: `extractDataParams()`** (`frontend/src/util.ts`)

```typescript
export function extractDataParams(elementId: string, names: string[]): ExtractedAttributes {
  const el = document.getElementById(elementId);
  if (el) {
    const attributes = names.reduce<ExtractedAttributes>((acc, name) => {
      // Convert camelCase to hyphenated: "versionNumber" -> "data-version-number"
      const hyphenatedName = name.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
      const attrValue = el.getAttribute(`data-${hyphenatedName}`);
      if (attrValue) {
        try {
          const parsedValue = JSON.parse(attrValue);  // handles objects, arrays, numbers
          acc[name] = parsedValue;
        } catch (error) {
          if (attrValue === "False") acc[name] = false;
          else if (attrValue === "True") acc[name] = true;
          else acc[name] = attrValue;                  // plain string
        }
      }
      return acc;
    }, {});
    return attributes;
  }
  return {};
}
```

### Complex Example: Release Retrieve Page

Multiple Vue apps mount on the same page:

```html
{# django/library/jinja2/library/codebases/releases/retrieve.jinja #}

{# Image gallery #}
<div id="image-gallery" class="my-4"
     data-title="{{ codebase.title }}"
     data-images="{{ codebase.get_image_urls()|tojson|forceescape }}">
</div>

{# Share URL regeneration #}
<div id="regenerate-share-uuid"
     data-version-number="{{ release.version_number }}"
     data-identifier="{{ codebase.identifier }}"
     data-initial-share-url="{{ request.build_absolute_uri(release.share_url) }}">
</div>

{# Download form #}
<div id="download-form"
     data-user-data="{{ get_download_request_metadata(request.user) }}"
     data-version-number="{{ release.version_number }}"
     data-identifier="{{ codebase.identifier }}">
</div>
```

Each `<div>` has its own Vue app mounted by a separate entry point. They share data through their `data-*` attributes, not through a shared store.

### `RootContextHTMLRenderer` -- The `__all__` Variable

```python
# core/renderers.py
class RootContextHTMLRenderer(TemplateHTMLRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        # ... resolve template ...
        context["__all__"] = data   # entire DRF response data
        return template.render(context, request=request)
```

Templates can access individual context keys (e.g., `{{ profile }}`, `{{ codebases }}`) set by the view, OR use `{{ __all__ }}` for the complete response payload. This is useful for passing serialized data to `data-*` attributes:

```html
{# Pass complex data as JSON to Vue via __all__ #}
<div id="my-app" data-config="{{ __all__|tojson|forceescape }}"></div>
```

### Jinja2 Context Globals

The `environment()` function in `core/jinja_config.py` adds globals available in ALL templates:

| Global | Purpose | Example |
|--------|---------|---------|
| `url(name, *args)` | Reverse URL | `{{ url('library:codebase-list') }}` |
| `static(path)` | Static file URL | `{{ static('images/logo.png') }}` |
| `markdown(text)` | Render markdown | `{{ markdown(codebase.description.raw) }}` |
| `to_json(value)` | JSON serialize | `{{ to_json(data) }}` |
| `format_date(obj)` | Date formatting | `{{ format_date(event.start_date) }}` |
| `constants` | Settings dict | `{{ constants.DEBUG }}`, `{{ constants.RELEASE_VERSION }}` |
| `get_download_request_metadata(user)` | User download metadata as JSON | For `data-user-data` attribute |

### When to Use Each Approach

| Scenario | Approach | Reason |
|----------|----------|--------|
| Static content page | Jinja2 only | No interactivity needed |
| List with filters/sort | Jinja2 page + Vue sidebar | Sidebar is interactive, list is server-rendered |
| Edit form | Jinja2 shell + Vue form component | Forms need validation, dynamic fields |
| Detail page with gallery | Jinja2 page + multiple Vue mounts | Gallery, download modal, share link are interactive islands |
| Multi-step workflow | Full SPA (release editor) | Complex state, step navigation, file uploads |

## Gotchas

- **`data-*` values must be escaped.** When passing JSON to `data-*` attributes, use `|tojson|forceescape` to prevent HTML injection. Plain strings from model fields are safe without `tojson`.
- **Python True/False in templates.** Django/Jinja2 renders Python booleans as `"True"` and `"False"`. `extractDataParams()` handles this conversion, but only for these exact strings.
- **Multiple Vue apps per page.** Several apps can mount on the same page (e.g., retrieve.jinja has image gallery, download form, and share URL regeneration). They are independent -- no shared state between them.
- **Template discovery path.** Templates live at `django/<app>/jinja2/<namespace>/<action>.jinja`. The `jinja2/` directory is required by Django's Jinja2 backend with `APP_DIRS = True`.
- **`vite_asset()` is a custom Jinja2 extension.** Defined in `core/jinja2ext.py` as `ViteExtension`. It reads `manifest.json` in production to resolve hashed bundle URLs.
- **The release editor is the exception.** It uses Vue Router for step navigation and Pinia for state. It mounts on `#release-editor` and manages its own routing. Do NOT add Vue Router to other apps.
- **CSRF token comes from cookie.** The `useAxios` composable reads `csrftoken` from `document.cookie` via an axios interceptor. No need to pass CSRF through `data-*` attributes.
- **No initial API call needed.** The Django template provides all bootstrap data via `data-*` attributes. Vue components should NOT make a "load initial data" API call on mount -- the data is already there in props.

## Extension

### Adding a new hybrid page

1. **Create/update the DRF ViewSet** (or use an existing one with `CommonViewSetMixin`)
2. **Create the Jinja2 template** at `django/<app>/jinja2/<namespace>/<action>.jinja`:
   ```html
   {% extends "base.jinja" %}
   {% block content %}
   <div id="my-mount"
        data-identifier="{{ object.identifier }}"
        data-config="{{ some_data|tojson|forceescape }}">
   </div>
   {% endblock %}
   {% block js %}
   {{ vite_asset("apps/my_app.ts") }}
   {% endblock %}
   ```
3. **Create the Vue entry point** at `frontend/src/apps/my_app.ts`:
   ```typescript
   import "vite/modulepreload-polyfill";
   import { createApp } from "vue";
   import MyComponent from "@/components/MyComponent.vue";
   import { extractDataParams } from "@/util";

   const props = extractDataParams("my-mount", ["identifier", "config"]);
   createApp(MyComponent, props).mount("#my-mount");
   ```
4. **Create the Vue component** at `frontend/src/components/MyComponent.vue`
5. **No Vite config change needed** -- auto-discovery picks up the new `.ts` file in `src/apps/`
