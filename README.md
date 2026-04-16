# Kalender — CalDAV Frontend

A dark-themed CalDAV web client with per-calendar colors, three calendar views, full event management, and event caching. Deployable as a single `docker compose up`.

## Quick Start

```bash
# Clone or copy this directory, then:
docker compose up -d
```

Open http://localhost:8080 and connect with your CalDAV server credentials.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT`   | `8080`  | Host port to expose the frontend on |

```bash
PORT=3000 docker compose up -d
```

## Compatible Servers

Works with any CalDAV-compliant server:

- **Nextcloud** — `https://your-nextcloud.com/remote.php/dav`
- **Radicale** — `http://radicale-host:5232`
- **Baikal** — `https://your-baikal.com/dav.php`
- **Fastmail** — `https://caldav.fastmail.com/dav/`
- **iCloud** — `https://caldav.icloud.com`

## Features

**Views**
- 📅 Month view — Monday-first week grid, events show start time and location
- 🗓️ Week view — hourly timeline, fits window height, click any slot to create
- 📋 Agenda view — 4-week rolling window from today, prev/next advances by 4 weeks

**Calendars**
- 🎨 Per-calendar color coding, auto-assigned on first connect
- ✅ Toggle individual calendar visibility (persisted across reloads)
- 🔄 Manual reload button — fetches fresh events on demand

**Events**
- ➕ Create events by clicking any day or hour slot, or via the sidebar button
- ✏️ Edit events — full field editing including calendar, time, location, recurrence
- 🗑️ Delete events from the detail view
- 📍 Location field — shown in all views before the description
- 🔁 Recurrence rules — daily, weekly, biweekly, monthly, yearly, or weekdays
- 📆 All-day event support

**UX**
- 💾 Server URL remembered across logouts; full credentials saved in session
- ⚡ Event cache — fetches an 8-week window once, navigating reuses cache
- 🕐 Date inputs in DD-MM-YYYY HH:MM 24h format
- 🐳 Single `docker compose up` deployment, no build step required

## Architecture

```
Browser → nginx (port 8080) → /api/* → FastAPI backend → CalDAV server
                            → /*     → Static HTML/JS (single file)
```

The FastAPI backend proxies all CalDAV communication server-side, handling authentication, XML parsing, and CORS. The frontend is a single self-contained HTML file with no build dependencies.

**Backend endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/calendars` | Discover all calendars for a principal |
| POST | `/api/events` | Fetch events for a calendar in a date range |
| POST | `/api/events/create` | Create a new event |
| POST | `/api/events/update` | Update an existing event (delete + recreate) |
| POST | `/api/events/delete` | Delete an event by URL |
| GET  | `/api/health` | Health check |

## AI Usage Note
This project was built entirely through an iterative conversation with [Claude](https://claude.ai) (Anthropic). No code was written by hand — the initial implementation, all feature additions, bug fixes, and this README were produced through natural language prompts and reviewed/tested by the user.
