# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

Vue 3 + TypeScript + Vite 7 front-end for an AI annotation studio. Supports bounding-box detection and polygon segmentation annotations in COCO format, with YOLO model training (real-time SSE monitoring + ECharts) and SAM3 WebSocket integration for AI-assisted segmentation.

**Stack:** Vue 3, Pinia (state), Vue Router (routing), Axios (HTTP), ECharts/vue-echarts (training charts), Element Plus (installed, CSS commented out — uncomment `import 'element-plus/dist/index.css'` in `main.ts` if using). Pure DOM/SVG for annotation canvas — **NOT** vue-konva (installed but unused).

**Runtime:** pnpm (required), Node `^20.19.0 || >=22.12.0`

**No ESLint. No tests.** Formatting via Prettier only.

## Build & Dev Commands

```bash
pnpm dev              # Dev server (0.0.0.0:5173)
pnpm build            # Type-check + production build (parallel via npm-run-all2)
pnpm build-only       # Production build without type-checking
pnpm type-check       # vue-tsc --build
pnpm preview          # Preview production build
pnpm format           # Prettier --write --experimental-cli src/
```

No test runner configured. If tests are added, check for Vitest/Jest configuration.

## Architecture

### Data Flow

```
View (local ref state) → API service (async arrow fn) → http.ts Axios interceptor → Backend
                                                              ↳ unwraps res.data → caller receives T directly
                                                              ↳ rejects if res.code !== 0 && res.code !== 200
```

The HTTP interceptor in `src/api/http.ts` **unwraps** `res.data` from the backend's `{ code, message, data }` envelope. API service callers receive the inner `T` directly, never the full envelope.

### Route Structure

```
/                                        → redirects to /task
/task                                    → DataAnnotationView → TaskListView
/task/:id                                → TaskDetail (image upload + list)
/task/:id/train                          → TrainTaskView → TrainingConfig + TrainMonitor
/task/:taskId/:imageName/detect          → DetectionAnnotationView (lazy-loaded)
/task/:taskId/:imageName/segment         → SegmentationAnnotationView (lazy-loaded)
```

`TrainTaskView` is a thin wrapper that provides `taskId` and `detectionType` to `TrainingConfig` via Vue `provide/inject`. `DataAnnotationView` is a thin wrapper around `TaskListView`.

### Annotation System (DOM/SVG — NOT Konva)

Two annotation components in `src/components/common/` follow the same pattern — accept type configs and annotations as props, emit events, expose imperative methods via `defineExpose`:

- **LabelComponents.vue** (bbox): Default export is `ImageRectDrawer`. Pure DOM `<div>` with `transform: translate(x,y)`. Exports `RectAnnotation` and `TypeConfig` types.
- **PolygonLabelComponents.vue** (polygon): SVG `<polygon>` overlay. Left-click adds points, right-click closes polygon. Exports `Point`, `PolygonAnnotation`, and `TypeConfig` types.

Both use `ResizeObserver` for responsive container sizing. Coordinates are normalized/scaled relative to displayed image size.

The annotation views manage the bridge between COCO format and the component's internal format:
- Load task categories → convert to `TypeConfig[]` via `categoriesToTypeConfigs()` with a fixed `COLOR_MAP`
- Load annotations from API → convert COCO `bbox`/`segmentation` to component format
- On save: convert component format back to COCO `CocoAnnotation[]` and call `updateAnnotation`

### SAM3 WebSocket (SegmentationAnnotationView only)

Two modes in the segmentation view:
- **draw mode**: Manual polygon drawing via `PolygonLabelComponents`
- **smart mode**: Click sends `point` action to SAM3 WebSocket, receives `contours` in COCO flat format `[x1,y1,x2,y2,...]`, draws them on a `<canvas>` overlay, user can apply results as polygon annotations

WebSocket lifecycle: `init` (sends s3_key) → `point` (repeated, incremental) → `reset` (clear points). Must cleanup in `onUnmounted`.

### Training Monitoring (TrainMonitor + SSE)

`TrainMonitor.vue` uses `EventSource` (created via `createTrainEventSource()` from `train.ts`) for real-time SSE updates. Displays progress bar, status badges (PENDING/RUNNING/FINISHED/ERROR), and four ECharts line charts: train loss, val loss, precision metrics (precision/recall/mAP50/mAP50-95), and learning rates.

### API Layer

```
src/api/
  http.ts              # Axios instance + interceptor (unwraps res.data)
  services/
    task.ts            # CRUD by task name (not ID): getTask, getTasks, createTask, updateTask, deleteTask
    image.ts           # Upload (multipart), list (paginated), get, delete by image_id
    annotation.ts      # getAnnotation (returns CocoDataset), updateAnnotation
    train.ts           # createTrain, getTrainList, getTrainStatus, getTrainMetrics,
                       #   getModelDownloadUrl, deleteTrain, createTrainEventSource (SSE)
    index.ts           # Barrel re-exports
```

All service functions are async arrow functions. The backend uses `task_name` as the key for task/image operations, not `task_id`. `train.ts` also duplicates `API_BASE_URL` for `EventSource` since the browser API doesn't use the Axios instance.

### Backend API Contract

Tasks are identified by `name` (not `id`) for all operations. Backend responses follow `{ success, message, data, code }` envelope. Delete operations are soft (sets `is_deleted=True`). Image URLs are RustFS presigned links with 1-hour expiry. Train config uses `extra = "forbid"` on the backend — sending unknown fields causes 422 errors.

Full API spec: see `api.md` in project root.

## Code Style & Conventions

### Formatting (Prettier — `.prettierrc.json`)
```json
{ "semi": false, "singleQuote": true, "printWidth": 100 }
```

### TypeScript
- **Always** use `import type` for type-only imports — never mix with value imports
- Type definitions in `src/types/` — one file per domain concept
- Path alias `@/*` → `./src/*` for all cross-module imports

### Vue Components (`<script setup lang="ts">`)
- Use `ref()` for all reactive state (consistency over `reactive()`)
- Props: `withDefaults(defineProps<Props>(), { ... })`
- Emits: `defineEmits<{ (e: 'event', payload: T): void }>()`
- Template refs: `const el = ref<HTMLElement | null>(null)` — always nullable

### Naming
| Item | Convention | Example |
|------|------------|---------|
| Vue files | PascalCase | `DetectionAnnotationView.vue` |
| TS modules | camelCase | `task.ts`, `annotation.ts` |
| Variables/Functions | camelCase, verb+noun | `getTasks`, `handleDeleteTask` |
| Types/Interfaces | PascalCase | `AssignmentDTO`, `CocoDataset` |
| CSS classes | kebab-case | `.task-card`, `.page-header` |

### Error Handling
- All API calls must use try/catch — log with `console.error` or re-throw
- Use `ElMessage.error()` / `ElMessage.success()` for user-facing notifications
- WebSocket: handle `onerror`/`onclose`, cleanup in `onUnmounted`

## Gotchas & Known Issues

- **Backend URL hardcoded** in `src/api/http.ts` (`http://172.16.0.72:8811/api`) and duplicated in `train.ts` — should use `VITE_API_BASE_URL` (no `.env` files exist yet)
- **WebSocket URL hardcoded** in `SegmentationAnnotationView.vue` (`ws://172.16.0.59:8811/ws/sam3`)
- **Duplicate `ApiResponse<T>`**: defined differently in `types/ApiResponse.ts` vs `api/http.ts` — the one in `http.ts` is what the interceptor actually uses; the types/ version is unused
- **`TrainingConfig.vue`** calls `http.post` directly instead of using `createTrain()` from `api/services/train.ts`
- **`TrainConfig` type** defined in `types/ImageItem.ts` — should be in its own file or `types/train.ts`
- **`composables/` empty**, `stores/` has only unused scaffold — large components (`SegmentationAnnotationView.vue` ~1478 lines, `TrainingConfig.vue` ~994 lines, `TaskListView.vue` ~863 lines) should extract logic here
- **konva + vue-konva** installed in dependencies but never imported — annotation uses pure DOM/SVG
- **Element Plus CSS** commented out in `main.ts` — uncomment if adding Element Plus components

## Pre-commit Checklist

1. `pnpm format` — format all modified files
2. `pnpm type-check` — verify no TypeScript errors
3. Use `import type` for type-only imports
4. Use `@/` alias for cross-module imports