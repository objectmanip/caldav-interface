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
    all_day: bool = False

class EventDeleteRequest(BaseModel):
    url: str
    username: str
    password: str
    calendar_url: str
    event_url: str


def get_client(url: str, username: str, password: str):
    return caldav.DAVClient(url=url, username=username, password=password)


def parse_event(event_obj):
    try:
        cal = Calendar.from_ical(event_obj.data)
        for component in cal.walk():
            if component.name == "VEVENT":
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

                return {
                    "uid": str(component.get("uid", "")),
                    "summary": str(component.get("summary", "(No Title)")),
                    "description": str(component.get("description", "")),
                    "start": start_str,
                    "end": end_str,
                    "all_day": all_day,
                    "url": str(event_obj.url),
                }
    except Exception:
        return None
    return None


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
            parsed = parse_event(ev)
            if parsed:
                result.append(parsed)

        return {"events": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/events/create")
async def create_event(req: EventCreateRequest):
    try:
        client = get_client(req.url, req.username, req.password)
        cal = client.calendar(url=req.calendar_url)

        if req.all_day:
            from datetime import date
            start_date = date.fromisoformat(req.start)
            end_date = date.fromisoformat(req.end)
            ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalDAV Frontend//EN
BEGIN:VEVENT
SUMMARY:{req.summary}
DESCRIPTION:{req.description}
DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}
DTEND;VALUE=DATE:{end_date.strftime('%Y%m%d')}
END:VEVENT
END:VCALENDAR"""
        else:
            start_dt = datetime.fromisoformat(req.start)
            end_dt = datetime.fromisoformat(req.end)
            ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalDAV Frontend//EN
BEGIN:VEVENT
SUMMARY:{req.summary}
DESCRIPTION:{req.description}
DTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}
END:VEVENT
END:VCALENDAR"""

        cal.save_event(ical)
        return {"status": "created"}
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
