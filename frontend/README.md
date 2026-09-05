# Cerebro Frontend Redesign

A lightweight static client for Cerebro using only HTML, CSS and vanilla JavaScript.

## Design rule

The browser is a human control and visualization surface. Python owns Cerebro's intelligence, job state, planning, permissions, approvals, execution, memory, providers and persistence.

## Visual system

- **Signature accent**: a cyan → indigo gradient (`--signal` / `--signal-2`), reserved for brand, primary actions, focus states, and "live" moments only.
- **Status colors** (amber/green/red/blue/violet) are semantic and untouched by the accent system, so meaning stays unambiguous at a glance.
- **Type**: Space Grotesk for headings, brand, and labels; IBM Plex Mono for data (job IDs, logs, metrics); Inter for body copy.
- Console-style details throughout: glass topbar with a live gradient hairline, glowing nav rail, node-based pipeline tracker, scanline terminal, pulsing "live" status dots.

## Files

- `index.html` — semantic application shell and views
- `css/base.css` — tokens, typography and resets
- `css/layout.css` — shell, navigation, responsive layout
- `css/components.css` — reusable UI components
- `css/views.css` — view-specific overrides
- `js/api.js` — REST/WebSocket boundary only
- `js/state.js` — small client-side presentation state
- `js/app.js` — routing, rendering and user interaction

## Backend contract

The prototype assumes:

- REST base: `/api`
- WebSocket: `/ws/events`

Suggested endpoints:

- `GET /api/jobs`
- `GET /api/jobs/{id}`
- `POST /api/jobs`
- `GET /api/jobs/{id}/tasks`
- `GET /api/jobs/{id}/events`
- `POST /api/jobs/{id}/approve`
- `POST /api/jobs/{id}/reject`
- `GET /api/projects`
- `GET /api/tools`
- `GET /api/providers`
- `GET /api/memory`
- `GET /api/system/health`

## Running locally

Because the finished backend will be Python, serve this folder rather than treating `file://` as the deployment model.

Example development server:

```bash
cd cerebro-frontend-redesign
python -m http.server 8080
```

Then visit `http://localhost:8080`.

No package manager, bundler, transpiler or frontend framework is required.
