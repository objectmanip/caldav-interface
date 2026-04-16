from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import caldav
from caldav.elements import dav
from icalendar import Calendar
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="CalDAV Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectRequest(BaseModel):
    url: str
    username: str
    password: str

class EventsRequest(BaseModel):
    url: str
    username: str
    password: str
    calendar_url: str
    start: Optional[str] = None
    end: Optional[str] = None

class EventCreateRequest(BaseModel):
    url: str
    username: str
    password: str
    calendar_url: str
    summary: str
    start: str
    end: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    rrule: Optional[str] = ""
    all_day: bool = False

class EventDeleteRequest(BaseModel):
    url: str
    username: str
    password: str
    calendar_url: str
    event_url: str

class EventUpdateRequest(BaseModel):
    url: str
    username: str
    password: str
    calendar_url: str
    event_url: str
    summary: str
    start: str
    end: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    rrule: Optional[str] = ""
    all_day: bool = False


def get_client(url: str, username: str, password: str):
    return caldav.DAVClient(url=url, username=username, password=password)


def parse_event(event_obj):
    """Parse all VEVENT components from a calendar object, returning a list."""
    results = []
    try:
        cal = Calendar.from_ical(event_obj.data)
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            try:
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")

                start_val = dtstart.dt if dtstart else None
                end_val = dtend.dt if dtend else None

                all_day = False
                if isinstance(start_val, datetime):
                    start_str = start_val.isoformat()
                    end_str = end_val.isoformat() if end_val else start_str
                else:
                    all_day = True
                    start_str = start_val.isoformat() if start_val else ""
                    end_str = end_val.isoformat() if end_val else start_str

                rrule_val = component.get("rrule")
                rrule_str = ""
                if rrule_val:
                    try:
                        rrule_str = rrule_val.to_ical().decode()
                    except Exception:
                        rrule_str = ""

                # Use recurrence-id or uid+start to make a unique URL-like key
                uid = str(component.get("uid", ""))
                recurrence_id = component.get("recurrence-id")
                url = str(event_obj.url)
                if recurrence_id:
                    url = f"{url}#{uid}-{start_str}"

                results.append({
                    "uid": uid,
                    "summary": str(component.get("summary", "(No Title)")),
                    "description": str(component.get("description", "")),
                    "location": str(component.get("location", "")),
                    "rrule": rrule_str,
                    "start": start_str,
                    "end": end_str,
                    "all_day": all_day,
                    "url": url,
                })
            except Exception:
                continue
    except Exception:
        pass
    return results


@app.post("/api/calendars")
async def get_calendars(req: ConnectRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        principal = client.principal()
        calendars = principal.calendars()
        result = []
        for cal in calendars:
            props = cal.get_properties([dav.DisplayName()])
            name = props.get("{DAV:}displayname", str(cal.url).split("/")[-2] or str(cal.url))
            result.append({"url": str(cal.url), "name": name})
        return {"calendars": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events")
async def get_events(req: EventsRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        cal = client.calendar(url=req.calendar_url)

        if req.start and req.end:
            start_dt = datetime.fromisoformat(req.start).replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(req.end).replace(tzinfo=timezone.utc)
            events = cal.date_search(start=start_dt, end=end_dt, expand=True)
        else:
            events = cal.events()

        result = []
        for ev in events:
            for parsed in parse_event(ev):
                result.append(parsed)

        return {"events": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def build_ical(summary, description, location, rrule, start, end, all_day):
    from datetime import date as date_type
    extra_lines = []
    if location:
        extra_lines.append(f"LOCATION:{location}")
    if rrule:
        extra_lines.append(f"RRULE:{rrule}")
    extra = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

    if all_day:
        start_date = date_type.fromisoformat(start)
        end_date = date_type.fromisoformat(end)
        return (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//CalDAV Frontend//EN\n"
            "BEGIN:VEVENT\n"
            f"SUMMARY:{summary}\n"
            f"DESCRIPTION:{description}\n"
            f"DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}\n"
            f"DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}"
            f"{extra}\n"
            "END:VEVENT\n"
            "END:VCALENDAR"
        )
    else:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//CalDAV Frontend//EN\n"
            "BEGIN:VEVENT\n"
            f"SUMMARY:{summary}\n"
            f"DESCRIPTION:{description}\n"
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}\n"
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}"
            f"{extra}\n"
            "END:VEVENT\n"
            "END:VCALENDAR"
        )


@app.post("/api/events/create")
async def create_event(req: EventCreateRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        cal = client.calendar(url=req.calendar_url)
        ical = build_ical(req.summary, req.description, req.location, req.rrule,
                          req.start, req.end, req.all_day)
        cal.save_event(ical)
        return {"status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/update")
async def update_event(req: EventUpdateRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        cal = client.calendar(url=req.calendar_url)
        try:
            old_event = cal.event_by_url(req.event_url)
            old_event.delete()
        except Exception:
            pass
        ical = build_ical(req.summary, req.description, req.location, req.rrule,
                          req.start, req.end, req.all_day)
        cal.save_event(ical)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/delete")
async def delete_event(req: EventDeleteRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        cal = client.calendar(url=req.calendar_url)
        event = cal.event_by_url(req.event_url)
        event.delete()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
