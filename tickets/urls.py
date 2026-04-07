from django.urls import path
from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────
    path('',                    views.index,          name='index'),

    # ── Auth ────────────────────────────────────────────────
    path('login/',              views.login_view,     name='login'),
    path('logout/',             views.logout_view,    name='logout'),

    # ── Admin / Technician ───────────────────────────────────
    path('dashboard/',          views.dashboard,      name='dashboard'),
    path('tickets/',            views.ticket_list,    name='ticket_list'),
    path('tickets/new/',        views.ticket_create,  name='ticket_create'),
    path('tickets/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('assignments/',        views.assignments,    name='assignments'),
    path('reports/',            views.reports,        name='reports'),
    path('technicians/',        views.technician_list, name='technician_list'),

    # ── Queue Public API (no login) ──────────────────────────
    path('api/queue/status/',   views.api_queue_status, name='api_queue_status'),
    path('api/queue/join/',     views.api_queue_join,   name='api_queue_join'),
    path('api/queue/leave/',    views.api_queue_leave,  name='api_queue_leave'),

    # ── Queue Admin API ──────────────────────────────────────
    path('api/queue/next/',     views.api_queue_next,   name='api_queue_next'),
    path('api/queue/resolve/',  views.api_queue_resolve, name='api_queue_resolve'),
    path('api/queue/skip/',     views.api_queue_skip,   name='api_queue_skip'),
    path('api/queue/serve/',    views.api_queue_serve,  name='api_queue_serve'),
    path('api/queue/remove/',   views.api_queue_remove, name='api_queue_remove'),

    # ── Legacy internal API ──────────────────────────────────
    path('api/assign/',         views.api_assign,     name='api_assign'),
    path('api/notification-check/', views.api_notification_check, name='api_notification_check'),

    # ── Public Rating (no login) ─────────────────────────────
    # path('api/queue/rate/',     views.api_queue_rate,   name='api_queue_rate'),

    # ── Technician Rating ─────────────────────────────────────
    path('api/technicians/<int:tech_id>/rate/', views.api_rate_technician, name='api_rate_technician'),
]
