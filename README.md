# RepairQ — IT Repair Queuing System (Django)

A full-featured IT repair ticket management system with queue management,
technician assignment, SLA tracking, and automated report generation.

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
python manage.py makemigrations tickets
python manage.py migrate
```

### 4. Seed demo data (technicians, tickets, report schedules)

```bash
python manage.py seed_data
```

### 5. Start the development server

```bash
python manage.py runserver
```

Open: http://127.0.0.1:8000

**Login:** `admin` / `admin`

---

## Project Structure

```
repairq/
├── manage.py
├── requirements.txt
├── repairq/                   # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── tickets/                   # Main application
    ├── models.py              # Ticket, Technician, TicketNote, ReportSchedule
    ├── views.py               # All page views + API endpoint
    ├── urls.py                # URL routing
    ├── admin.py               # Django admin configuration
    ├── management/
    │   └── commands/
    │       └── seed_data.py   # Demo data seeder
    └── templates/tickets/
        ├── base.html          # Sidebar, topbar, layout
        ├── login.html
        ├── dashboard.html
        ├── ticket_list.html
        ├── ticket_detail.html
        ├── ticket_create.html
        ├── assignments.html
        ├── reports.html
        └── technician_list.html
```

---

## Pages & URLs

| URL                        | Page                     |
|----------------------------|--------------------------|
| `/`                        | Dashboard                |
| `/login/`                  | Login                    |
| `/tickets/`                | Ticket Queue (filterable)|
| `/tickets/new/`            | Submit New Ticket        |
| `/tickets/<ticket_id>/`    | Ticket Detail & Update   |
| `/assignments/`            | Assign Technicians       |
| `/reports/`                | Report Engine            |
| `/technicians/`            | Technician Roster        |
| `/admin/`                  | Django Admin Panel       |

---

## Features

- **Ticket Queue** — Filter by status, priority, technician, or free-text search
- **Ticket Detail** — Full activity timeline, status updates, diagnostic notes, escalation
- **Auto SLA** — SLA deadlines calculated on creation based on priority level
  - Critical: 4h | High: 8h | Medium: 48h | Low: 120h
- **Assignments** — Workload balancer, unassigned queue, one-click assign
- **Reports** — Daily / Weekly / Monthly KPIs, category breakdown, technician performance
- **Technician Management** — Skills, availability, open ticket count
- **Django Admin** — Full CRUD for all models at `/admin/`

---

## Moving to Production

1. Set `DEBUG = False` in `settings.py`
2. Change `SECRET_KEY` to a secure random value (use environment variable)
3. Set `ALLOWED_HOSTS` to your actual domain
4. Switch to PostgreSQL:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'repairq',
           'USER': 'your_db_user',
           'PASSWORD': 'your_db_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```
5. Run `python manage.py collectstatic` and serve static files via nginx/whitenoise
6. Use `gunicorn repairq.wsgi` as the WSGI server

---

## Extending the System

- **Email notifications**: Add Django's email backend + signals on `Ticket.save()`
- **REST API**: Add `djangorestframework` and create serializers in `tickets/serializers.py`
- **CSV/PDF export**: Add `reportlab` (PDF) and use Python's built-in `csv` module
- **Celery tasks**: Schedule report delivery with Celery + Redis
- **User self-registration**: Add a signup view and link it to `Technician` model
