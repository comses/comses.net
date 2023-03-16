# frontend-next

CoMSES Net frontend components with Vue 3/Typescript/Vite. Work in progress that will eventually replace the current vue 2 frontend components/service.

## Structure

- `src/` - source code
  - `apps/` - entry points that mount widgets, optionally reading data attributes
  - `components/` - components - use flat directory structure with naming prefixes for organization
  - `composables/` - reusable composition functions
  - `stores/` - pinia stores
  - `scss/` - global sass stylesheets
  - `assets/` - static assets
  - `vite.config.ts` - vite configuration - new 'apps' must be added to `build.rollupOptions.input`

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (disable vetur and [enable volar takeover mode](https://vuejs.org/guide/typescript/overview.html#volar-takeover-mode))

## Operations

### Build and deploy all containers (including hot-reloading vite dev server)

```sh
make deploy
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
docker compose exec vite yarn test # run all tests once
# OR
docker compose exec vite yarn yarn test:watch # run all tests watching for file changes
```

### Run type-checker

```sh
docker compose exec vite yarn type-check
```

### Linting/formatting

```sh
docker compose exec vite yarn lint # lint:fix to attempt to fix linting errors
docker compose exec vite yarn format # format:fix to fix formatting errors
```
