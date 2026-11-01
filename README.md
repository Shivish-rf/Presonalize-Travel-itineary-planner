# Treavue — Personalized Travel Itinerary Planner

Treavue is a travel-planning web application designed to help travelers explore destinations, organize trip details, save places of interest, and shape an itinerary around dates, budget, travel style, and personal preferences. The interface is built around a calm, editorial travel aesthetic and a structured trip notebook.

This README documents the source archive supplied for this task. In that snapshot, trip and preference data are stored in browser `localStorage`, while the separate Express API is a starter service exposing a health-check endpoint. A production-ready FastAPI/Supabase service, live booking integration, live route optimization, and server-backed authentication are **not present in the supplied archive** and should not be presented as completed features unless they are available in the version you deploy.

---

## Table of Contents

- [Core Capabilities](#core-capabilities)
- [Application Architecture & Data Flow](#application-architecture--data-flow)
- [Technology Stack](#technology-stack)
- [Project Directory Structure](#project-directory-structure)
- [Installation & Setup (Windows)](#installation--setup-windows)
- [Environment Configuration](#environment-configuration)
- [Running the Frontend](#running-the-frontend)
- [Running the API Service](#running-the-api-service)
- [Build & Type Checks](#build--type-checks)
- [Routes & API Reference](#routes--api-reference)
- [Data Model & Persistence](#data-model--persistence)
- [Known Limitations & Future Work](#known-limitations--future-work)
- [Privacy, Security & Responsible Use](#privacy-security--responsible-use)

---

## Core Capabilities

### 1. Destination Discovery
- **Destination catalogue:** Browse a curated set of destinations with descriptions, regions, interests, attraction highlights, local food notes, and travel tips.
- **Search and filters:** Search by place or country, and filter destinations by interest or region.
- **Sorting:** Sort the destination list alphabetically or by the indicative daily budget field.
- **Destination details:** Review highlights and planning notes for a selected destination.

### 2. Trip Planning Workspace
- **Trip setup:** Collect a destination, trip name, date range, traveler type and count, budget, interests, and preferred pace.
- **Travel preferences:** Capture transport, accommodation, dietary needs, accessibility needs, must-visit places, and additional instructions in the trip-planning form.
- **Trip workspace:** Open a saved trip to review its planned days and activities and access itinerary editing controls present in the interface.
- **Trip organization:** View trips, search or filter the trip list, and manage trip records through the user interface.

> Itinerary quality depends on the itinerary data and logic bundled with the particular version. The supplied archive includes local seed/sample data; it does not demonstrate a guaranteed AI-generated itinerary or real-time availability check.

### 3. Saved Places & Favorites
- Save destination and attraction ideas for later reference.
- Maintain a favorites list and review saved places in a dedicated page.
- Use saved items as a planning reference while organizing a trip.

### 4. Profile & Travel Preferences
- Edit profile-style information such as name, email, home location, currency, travel style, and interests in the UI.
- Reuse stored preferences in the local demonstration experience.

### 5. Navigation & Responsive Interface
- Client-side navigation for Dashboard, Explore, Destination Details, Plan, Trips, Trip Workspace, Saved, Guides, Profile, and account-related screens.
- React component structure, reusable UI controls, utility styling, and icons support a consistent interface.
- Dedicated not-found handling for routes that do not match a known page.

### 6. API Service Scaffold
- A separate Express application provides `GET /api/healthz` for a basic service health check.
- Request logging, JSON request parsing, URL-encoded request parsing, and CORS middleware are configured.
- The API and database packages are workspace scaffolding; the supplied archive does not contain a completed travel-specific REST API or populated Drizzle schema.

---

## Application Architecture & Data Flow

```text
                         TRAVELER
                            │
                            ▼
                 ┌──────────────────────┐
                 │ React + Vite Frontend│
                 │ Dashboard / Explore  │
                 │ Plan / Trips / Saved │
                 │ Profile / Guides     │
                 └───────────┬──────────┘
                             │
                    Read / update Store
                             │
                             ▼
                 ┌──────────────────────┐
                 │ Browser localStorage │
                 │ treavue-demo-store-v1│
                 │ destinations, trips, │
                 │ saved, favorites,    │
                 │ profile              │
                 └──────────────────────┘

          Optional, separate workspace API service
                             │
                             ▼
                 ┌──────────────────────┐
                 │ Express 5 API        │
                 │ /api/healthz         │
                 └──────────────────────┘

       PostgreSQL/Drizzle packages are scaffolded in the
       repository; the supplied schema contains no app tables.
```

**Current data flow:** The frontend reads its initial state with `readStore()`. If valid local data is not found, it creates a seeded store and writes it to browser storage. User actions update the shared store and persist the result with `writeStore()`. This is local browser persistence, not a multi-user cloud database.

---

## Technology Stack

| Component | Technology | Role in the supplied source archive |
|---|---|---|
| **Frontend framework** | React, TypeScript | Application components, pages, and state handling |
| **Frontend tooling** | Vite | Development server and production build |
| **Routing** | Wouter | Client-side page navigation |
| **UI components** | Radix UI, reusable local components | Accessible interface primitives and dialogs/controls |
| **Styling** | Tailwind CSS / `@tailwindcss/vite`, CSS | Layout, visual system, responsive styling |
| **Icons and charts** | Lucide React, Recharts | Interface icons and visualization utilities |
| **Frontend state persistence** | Browser `localStorage` | Persists the demonstration store on the current browser/device |
| **API service** | Node.js, TypeScript, Express 5 | Separate API scaffold; currently exposes a health endpoint |
| **API validation/contracts** | OpenAPI, Zod-generated workspace packages | Contract and validation tooling scaffold |
| **Database layer** | PostgreSQL, `pg`, Drizzle ORM | Workspace database scaffold; schema has no Treavue tables in this snapshot |
| **Package management** | pnpm workspaces | Installs and coordinates the monorepo packages |
| **Type checking** | TypeScript compiler | Checks frontend and workspace packages |

No dedicated machine-learning model or external generative-AI provider is configured in the supplied source archive. Do not describe the current code as using a specific AI model unless one is added and verified in the active repository.

---

## Project Directory Structure

```text
Treavue-Travel-Planner/
├── artifacts/
│   ├── treavue/                   # Main React + Vite frontend
│   │   ├── src/
│   │   │   ├── App.tsx             # Application routes and store wiring
│   │   │   ├── components/         # Shell and reusable components
│   │   │   ├── hooks/              # UI hooks
│   │   │   ├── lib/
│   │   │   │   ├── data.ts         # Curated destination and seed data
│   │   │   │   ├── storage.ts      # localStorage read/write helpers
│   │   │   │   ├── types.ts        # Destination, Trip, Day, Activity, Store types
│   │   │   │   └── utils.ts        # Shared utilities
│   │   │   ├── pages/Pages.tsx     # Main page and workflow components
│   │   │   ├── index.css           # Global styling
│   │   │   └── main.tsx            # Frontend entry point
│   │   ├── index.html
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── api-server/                 # Express API service scaffold
│   │   └── src/
│   │       ├── app.ts              # Express middleware and /api router
│   │       ├── index.ts            # API server entry point
│   │       └── routes/
│   │           ├── index.ts
│   │           └── health.ts       # GET /api/healthz
│   └── mockup-sandbox/             # UI mockup/sandbox workspace
├── lib/
│   ├── api-client-react/           # Generated/client API helpers
│   ├── api-spec/                   # OpenAPI contract
│   ├── api-zod/                    # Generated schema types
│   └── db/                         # PostgreSQL/Drizzle setup and schema exports
├── scripts/                        # Workspace scripts
├── package.json                    # Root workspace scripts
├── pnpm-lock.yaml
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── tsconfig.json
└── replit.md                       # Workspace run and stack notes
```

---

## Installation & Setup (Windows)

### Prerequisites
- **Operating System:** Windows 10 or 11 (64-bit).
- **Node.js:** Use the Node version compatible with the project workspace; the supplied project was previously run with Node.js 24.
- **pnpm:** Required package manager. The project includes a `pnpm-lock.yaml` and a pnpm workspace configuration.
- **Git Bash or WSL (recommended for workspace scripts):** Some scripts use Unix shell syntax such as `sh` and `export`, which may not execute directly in PowerShell without a compatible shell.

### Step 1: Open the Project Folder
In PowerShell, navigate to the directory containing the root `package.json`:

```powershell
cd "C:\path\to\Treavue-Travel-Planner"
```

### Step 2: Install Dependencies
Run from the repository root:

```powershell
pnpm install
```

If a workspace lifecycle script fails because `sh` is not available, run the install from Git Bash/WSL or update the script to use a Windows-compatible command. Do not delete the lockfile merely to bypass a dependency-resolution error unless you intend to regenerate and review it.

---

## Environment Configuration

The main frontend Vite configuration requires both `PORT` and `BASE_PATH` to be set before startup.

In PowerShell, configure them for the current terminal session:

```powershell
$env:PORT = "5173"
$env:BASE_PATH = "/"
```

For the separate API service, set its port before starting it:

```powershell
$env:PORT = "8001"
```

The repository's database package expects a `DATABASE_URL` connection string if the database module is used:

```powershell
$env:DATABASE_URL = "postgresql://USER:PASSWORD@HOST:PORT/DATABASE"
```

Replace the example values with your own local development credentials. The supplied frontend does not require a Supabase key to use its `localStorage` demo store. Never commit real database credentials, API keys, or `.env` secrets to GitHub.

---

## Running the Frontend

From the repository root, set the required Vite environment variables and start the frontend package:

```powershell
$env:PORT = "5173"
$env:BASE_PATH = "/"
pnpm --filter @workspace/treavue dev
```

Open the URL printed by Vite, usually `http://localhost:5173` when port `5173` is configured.

Available frontend routes include:

| Route | Purpose |
|---|---|
| `/` | Dashboard |
| `/explore` | Browse and filter destinations |
| `/destinations/:id` | Destination details |
| `/plan` | Create a trip plan |
| `/trips` | View and manage trip records |
| `/trips/:id` | Open a trip workspace |
| `/saved` | Saved destinations and places |
| `/guides` | Destination guides |
| `/profile` | Edit profile-style preferences |
| `/auth/sign-in` | Sign-in screen UI |
| `/auth/sign-up` | Sign-up screen UI |
| `/auth/forgot-password` | Password-recovery screen UI |

The account routes represent interface screens in the supplied archive; they should not be interpreted as proof of working server-backed authentication.

---

## Running the API Service

The separate API service is an Express application. Its current development script contains Unix shell syntax, so Git Bash/WSL is the most compatible shell unless the script is adjusted for Windows.

Set a port and run from the repository root:

```bash
export PORT=8001
pnpm --filter @workspace/api-server run dev
```

The service exposes one confirmed endpoint in the supplied archive:

```http
GET /api/healthz
```

Expected response:

```json
{"status":"ok"}
```

The endpoint is a basic service-health check. The supplied archive does not implement trip CRUD routes, user authentication routes, or Supabase integration in this Express service.

---

## Build & Type Checks

Run these commands from the repository root after installing dependencies:

```powershell
pnpm run typecheck
pnpm run build
```

- `pnpm run typecheck` runs the configured TypeScript checks across workspace libraries and selected artifacts.
- `pnpm run build` runs type checking and then invokes the configured build scripts across the workspace packages.

A successful type check or build verifies the relevant compile-time/build steps; it does not prove that all user flows, database operations, authentication, itinerary quality, or third-party integrations work end to end. No automated application test suite was identified in the supplied archive.

---

## Routes & API Reference

### Frontend routes

The React router in `artifacts/treavue/src/App.tsx` defines the dashboard, destination discovery and detail pages, trip planner, trip list and workspace, saved places, guides, profile, and account-related pages.

### API endpoint

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/healthz` | Returns an API health status of `ok` |

No other travel API endpoints are defined in the supplied OpenAPI specification. Add an endpoint to the API implementation and update the OpenAPI contract before listing any additional API route here.

---

## Data Model & Persistence

The frontend's TypeScript types include:

- **Destination:** Name, country, region, description, image, interests, suggested length, indicative budget, attractions, cuisine, and tips.
- **Trip:** Destination, dates, travelers, budget, preferences, transport, accommodation, dietary/accessibility needs, activities by day, status, and notes.
- **Day and Activity:** Date-level itinerary groups and activity details such as location, time, duration, category, estimated cost, notes, and whether an activity is fixed.
- **SavedPlace:** A saved attraction, restaurant, destination, or activity reference.
- **Profile:** Name, email, home location, currency, travel style, and interests.
- **Store:** Collections of destinations, trips, saved places, favorites, and profile information.

The local demonstration store uses the key `treavue-demo-store-v1`. Because the data resides in browser storage, it is tied to that browser profile and device. Clearing browser data may remove saved demo state; it is not a cloud sync or backup mechanism.

---

## Known Limitations & Future Work

1. **Local-only persistence:** The supplied frontend writes state to `localStorage`; a production app needs a secure server-backed data store and per-user ownership rules.
2. **Authentication:** The archive includes sign-in, sign-up, and password-recovery screens, but does not include a completed authentication provider flow in the shown frontend/API code.
3. **Backend implementation:** The Express API currently contains a health endpoint only. A complete travel backend, itinerary endpoints, and data validations need to be implemented and tested before describing them as available.
4. **Database schema:** The Drizzle schema export is a placeholder in this snapshot. Database tables, migrations, constraints, and ownership relationships need to be defined before database-backed functionality can be claimed.
5. **Travel data freshness:** Destination descriptions and budget figures are curated/demo values. They are not a substitute for checking current travel advisories, local opening times, weather, transport disruption, visa rules, or venue availability.
6. **Pricing and itinerary quality:** Budget figures and activity costs are indicative. They are not live quotes or booking confirmations. Itineraries should be reviewed for travel time, opening hours, accessibility, and individual needs.
7. **AI and live integrations:** No dedicated AI model, live map/routing service, booking provider, or live-price API is configured in the supplied archive.
8. **Windows scripts:** A few package scripts rely on Unix shell syntax. Git Bash/WSL or Windows-compatible script adjustments may be needed.

Suggested next steps are to complete the intended backend integration, implement and verify authentication, connect the data layer, add API/integration tests, and document only those integrations that have been tested against the deployed version.

---

## Privacy, Security & Responsible Use

- Never commit passwords, access tokens, database URLs, Supabase service-role keys, or other secrets to version control.
- Do not place privileged database credentials in browser-side code. Keep secrets on a server and enforce authentication and authorization there.
- Before supporting multiple users, verify ownership on every trip read, create, update, and delete operation, and apply appropriate database row-level security where supported.
- Avoid storing sensitive identity, health, payment, or travel-document information in the current browser-only demo store.
- Verify travel information with authoritative providers before making bookings or safety-critical decisions.

Treavue is a planning aid. This source snapshot does not book travel, guarantee availability, verify live safety conditions, or provide professional travel or legal advice.
