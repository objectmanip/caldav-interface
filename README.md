# Kalender — CalDAV Frontend

A minimal, dark-themed CalDAV web client with per-calendar colors, month/week/agenda views, and event creation/deletion.

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

- **Nextcloud** — URL: `https://your-nextcloud.com/remote.php/dav`
- **Radicale** — URL: `http://radicale-host:5232`
- **Baikal** — URL: `https://your-baikal.com/dav.php`
- **Fastmail** — URL: `https://caldav.fastmail.com/dav/`
- **iCloud** — URL: `https://caldav.icloud.com`

## Features

- 📅 Month, Week, and Agenda views
- 🎨 Per-calendar color coding (auto-assigned, saved in browser)
- ✅ Toggle calendar visibility
- ➕ Create new events (timed or all-day)
- 🗑️ Delete events
- 💾 Credentials saved in localStorage (cleared on logout)
- 🐳 Single `docker compose up` deployment

## Architecture

```
Browser → nginx (port 8080) → /api/* → FastAPI backend → CalDAV server
                            → /*     → Static HTML/JS
```

The FastAPI backend acts as a proxy, handling CalDAV protocol details (HTTPS, auth, XML parsing) server-side to avoid CORS issues.
