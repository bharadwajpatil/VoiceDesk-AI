"""FastAPI Backend Server and Dashboard for VoiceDesk AI.

Provides REST APIs and an intuitive web dashboard to view, filter, and manage
appointments, track Google Calendar synchronization, and inspect business details.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config
from database.appointments_db import init_db
from services.appointment_service import AppointmentService
from services.calendar_service import get_calendar_service

app = FastAPI(
    title="VoiceDesk AI Dashboard & API",
    description="Backend service for VoiceDesk AI Voice Receptionist",
    version="1.0.0",
)

# Enable CORS for external frontend or local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables exist on server startup
init_db()


class AppointmentUpdateRequest(BaseModel):
    status: str | None = None
    notes: str | None = None


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "VoiceDesk AI"}


@app.get("/api/calendar/status")
def get_calendar_status() -> dict[str, Any]:
    """Check whether Google Calendar OAuth is active and connected."""
    cal_service = get_calendar_service()
    is_conn = cal_service.is_connected()
    return {
        "configured": cal_service.is_configured(),
        "connected": is_conn,
        "calendar_id": config.GOOGLE_CALENDAR_ID if is_conn else None,
        "token_file": str(Path(config.GOOGLE_TOKEN_FILE).name),
    }


@app.get("/api/business")
def get_business_details() -> dict[str, str]:
    """Retrieve configured business information."""
    return {
        "name": config.BUSINESS_NAME,
        "type": config.BUSINESS_TYPE,
        "hours": config.BUSINESS_HOURS,
        "location": config.BUSINESS_LOCATION,
        "services": config.BUSINESS_SERVICES,
        "policies": config.BUSINESS_POLICIES,
        "timezone": config.BUSINESS_TIMEZONE,
    }


@app.get("/api/appointments")
def list_appointments(
    status: str | None = Query(
        None, description="Filter by status (pending, confirmed, cancelled)"
    ),
    date: str | None = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """List appointments with optional status and date filters."""
    service = AppointmentService()
    return service.list(status=status, date_filter=date, limit=limit, offset=offset)


@app.get("/api/appointments/{appointment_id}")
def get_appointment(appointment_id: int) -> dict[str, Any]:
    """Get appointment by ID."""
    service = AppointmentService()
    record = service.get(appointment_id)
    if not record:
        raise HTTPException(
            status_code=404, detail=f"Appointment {appointment_id} not found"
        )
    return record


@app.post("/api/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int) -> dict[str, Any]:
    """Cancel an appointment and sync cancellation with Google Calendar."""
    service = AppointmentService()
    success, message = service.cancel(appointment_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@app.get("/", response_class=HTMLResponse)
def serve_dashboard() -> str:
    """Serve the modern VoiceDesk AI Web Dashboard."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VoiceDesk AI — Receptionist Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(22, 28, 45, 0.75);
      --border: rgba(255, 255, 255, 0.08);
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 2rem 1.5rem; min-height: 100vh; }
    .container { max-width: 1200px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }
    .brand { display: flex; align-items: center; gap: 0.75rem; }
    .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; font-weight: 700; color: white; }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .badge { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; padding: 0.35rem 0.75rem; border-radius: 9999px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge.offline { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; backdrop-filter: blur(12px); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2); }
    .stat-title { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .stat-val { font-size: 2rem; font-weight: 700; }
    .table-container { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; backdrop-filter: blur(12px); }
    .table-header { padding: 1.25rem 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th { padding: 1rem 1.5rem; font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; background: rgba(255, 255, 255, 0.02); }
    td { padding: 1.15rem 1.5rem; border-bottom: 1px solid var(--border); font-size: 0.92rem; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .status-pill { padding: 0.25rem 0.65rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; text-transform: capitalize; }
    .status-confirmed { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .status-cancelled { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .btn { background: var(--primary); color: white; border: none; padding: 0.45rem 0.9rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: all 0.2s; }
    .btn:hover { background: var(--primary-hover); }
    .btn-danger { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.35); }
    .empty-state { text-align: center; padding: 3rem; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="logo-icon">V</div>
        <div>
          <h1>VoiceDesk AI</h1>
          <p style="font-size: 0.85rem; color: var(--text-muted);">Receptionist Control Center</p>
        </div>
      </div>
      <div id="calendar-badge" class="badge">
        <span style="font-size: 0.7rem;">●</span> Checking Calendar...
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <div class="stat-title">Total Bookings</div>
        <div id="stat-total" class="stat-val">0</div>
      </div>
      <div class="card">
        <div class="stat-title">Confirmed</div>
        <div id="stat-confirmed" class="stat-val" style="color: #34d399;">0</div>
      </div>
      <div class="card">
        <div class="stat-title">Pending</div>
        <div id="stat-pending" class="stat-val" style="color: #fbbf24;">0</div>
      </div>
      <div class="card">
        <div class="stat-title">Google Calendar</div>
        <div id="stat-cal" class="stat-val" style="font-size: 1.25rem; font-weight: 600;">Sync Active</div>
      </div>
    </div>

    <div class="table-container">
      <div class="table-header">
        <h2 style="font-size: 1.15rem; font-weight: 600;">Recent Appointment Bookings</h2>
        <button onclick="fetchData()" class="btn">Refresh Data</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Customer</th>
            <th>Phone</th>
            <th>Date & Time</th>
            <th>Service</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="appointments-tbody">
          <tr><td colspan="7" class="empty-state">Loading appointments...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <script>
    async function fetchData() {
      try {
        const [calRes, aptRes] = await Promise.all([
          fetch('/api/calendar/status'),
          fetch('/api/appointments')
        ]);
        const cal = await calRes.json();
        const appointments = await aptRes.json();

        // Update Calendar Status
        const badge = document.getElementById('calendar-badge');
        const statCal = document.getElementById('stat-cal');
        if (cal.connected) {
          badge.className = 'badge';
          badge.innerHTML = '● Google Calendar: Connected';
          statCal.textContent = 'Connected (Live)';
          statCal.style.color = '#34d399';
        } else {
          badge.className = 'badge offline';
          badge.innerHTML = '● Google Calendar: Not Connected';
          statCal.textContent = 'Not Connected';
          statCal.style.color = '#f87171';
        }

        // Stats
        document.getElementById('stat-total').textContent = appointments.length;
        document.getElementById('stat-confirmed').textContent = appointments.filter(a => a.status === 'confirmed').length;
        document.getElementById('stat-pending').textContent = appointments.filter(a => a.status === 'pending').length;

        // Render Table
        const tbody = document.getElementById('appointments-tbody');
        if (appointments.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No appointments recorded yet.</td></tr>';
          return;
        }

        tbody.innerHTML = appointments.map(apt => `
          <tr>
            <td><strong>#${apt.id}</strong></td>
            <td>${apt.customer_name}</td>
            <td>${apt.customer_phone}</td>
            <td>${apt.appointment_date} at ${apt.appointment_time}</td>
            <td>${apt.service_type}</td>
            <td><span class="status-pill status-${apt.status}">${apt.status}</span></td>
            <td>
              ${apt.status !== 'cancelled' ? `<button onclick="cancelApt(${apt.id})" class="btn btn-danger">Cancel</button>` : '<span style="color: var(--text-muted); font-size: 0.85rem;">Cancelled</span>'}
            </td>
          </tr>
        `).join('');

      } catch (err) {
        console.error('Error fetching dashboard data:', err);
      }
    }

    async function cancelApt(id) {
      if (!confirm(`Are you sure you want to cancel appointment #${id}?`)) return;
      try {
        const res = await fetch(`/api/appointments/${id}/cancel`, { method: 'POST' });
        if (res.ok) {
          fetchData();
        } else {
          alert('Failed to cancel appointment');
        }
      } catch (err) {
        alert('Error: ' + err);
      }
    }

    fetchData();
    // Auto-refresh every 15 seconds
    setInterval(fetchData, 15000);
  </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
