from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Avg, Count, Q, F
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from .models import Ticket, Technician, TicketNote, ReportSchedule


# ── Public View ───────────────────────────────────────────────

def index(request):
    """
    Public-facing Tech Support Desk page.
    Allows users to join the queue without signing in.
    """
    now_serving = Ticket.objects.filter(status='in_progress').order_by('-updated_at').first()
    waiting     = Ticket.objects.filter(status='received').order_by('created_at')

    context = {
        'now_serving':   now_serving,
        'waiting':       waiting,
        'waiting_count': waiting.count(),
        'active_page':   'index',
    }
    return render(request, 'tickets/index.html', context)


# ── Auth ──────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            if user.is_staff or hasattr(user, 'technician'):
                return redirect('dashboard')
            return redirect('index')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'tickets/login.html')


def logout_view(request):
    logout(request)
    return redirect('index')


# ── Dashboard ─────────────────────────────────────────────────

@login_required
def dashboard(request):
    # Only staff/tech should see the dashboard
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')

    now = timezone.now()
    open_statuses = ['received', 'triaged', 'assigned', 'in_progress']
    tickets_qs = Ticket.objects.all()

    # Filter for technician
    if hasattr(request.user, 'technician'):
        tickets_qs = tickets_qs.filter(assigned_to=request.user.technician)

    open_count      = tickets_qs.filter(status__in=open_statuses).count()
    in_progress     = tickets_qs.filter(status='in_progress').count()
    overdue_count   = tickets_qs.filter(status__in=open_statuses, sla_due_at__lt=now).count()
    resolved_today  = tickets_qs.filter(status__in=['resolved', 'closed'],
                                             resolved_at__date=now.date()).count()

    recent_tickets  = tickets_qs.select_related('assigned_to', 'submitted_by').order_by('-created_at')[:8]
    overdue_tickets = tickets_qs.filter(status__in=open_statuses, sla_due_at__lt=now)
    technicians     = Technician.objects.all()

    context = {
        'open_count':     open_count,
        'in_progress':    in_progress,
        'overdue_count':  overdue_count,
        'resolved_today': resolved_today,
        'recent_tickets': recent_tickets,
        'overdue_tickets': overdue_tickets,
        'technicians':    technicians,
        'active_page':    'dashboard',
    }
    return render(request, 'tickets/dashboard.html', context)


# ── Ticket Queue ──────────────────────────────────────────────

@login_required
def ticket_list(request):
    qs = Ticket.objects.select_related('assigned_to', 'submitted_by').all()

    # Only staff/tech should see management views
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')

    status   = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    tech_id  = request.GET.get('technician', '')
    q        = request.GET.get('q', '')
    overdue  = request.GET.get('overdue', '')
    resolved_today = request.GET.get('resolved_today', '')

    if status:
        if ',' in status:
            qs = qs.filter(status__in=status.split(','))
        else:
            qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if tech_id:
        qs = qs.filter(assigned_to_id=tech_id)
    if overdue == '1':
        now = timezone.now()
        qs = qs.exclude(status__in=['resolved', 'closed']).filter(sla_due_at__lt=now)
    if resolved_today == '1':
        now = timezone.now()
        qs = qs.filter(status__in=['resolved', 'closed'], resolved_at__date=now.date())
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=q) | Q(ticket_id__icontains=q) | Q(description__icontains=q))

    technicians = Technician.objects.all()
    now         = timezone.now()
    open_statuses = ['received', 'triaged', 'assigned', 'in_progress']

    now_serving = Ticket.objects.filter(status='in_progress').order_by('-updated_at').first()
    waiting_count = Ticket.objects.filter(status='received').count()

    context = {
        'tickets':     qs,
        'technicians': technicians,
        'now':         now,
        'filter_status':   status,
        'filter_priority': priority,
        'filter_tech':     tech_id,
        'filter_q':        q,
        'active_page': 'tickets',
        'overdue_count': qs.filter(status__in=open_statuses, sla_due_at__lt=now).count(),
        'now_serving': now_serving,
        'waiting_count': waiting_count,
        'serving_count': 1 if now_serving else 0,
        'resolved_today': Ticket.objects.filter(status__in=['resolved', 'closed'], resolved_at__date=now.date()).count(),
        'urgent_count': Ticket.objects.filter(status='received', priority__in=['high', 'critical']).count(),
    }
    return render(request, 'tickets/ticket_list.html', context)


# ── Ticket Detail ─────────────────────────────────────────────

@login_required
def ticket_detail(request, ticket_id):
    ticket      = get_object_or_404(Ticket, ticket_id=ticket_id)
    # Staff and technicians can view any ticket. Others (public) must be the owner.
    is_staff = request.user.is_staff or hasattr(request.user, 'technician')
    is_owner = ticket.submitted_by == request.user
    
    if not is_staff and not is_owner:
        messages.error(request, 'Access denied.')
        return redirect('index')

    is_tech = hasattr(request.user, 'technician') and ticket.assigned_to == request.user.technician
    notes       = ticket.notes.select_related('author').order_by('created_at')
    technicians = Technician.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            old_status = ticket.status
            new_status = request.POST.get('status')
            assignee_id = request.POST.get('assigned_to')
            location = request.POST.get('location', '').strip()
            note_content = request.POST.get('note', '').strip()

            # Check permission: Only assigned tech or superuser
            is_assigned = hasattr(request.user, 'technician') and ticket.assigned_to == request.user.technician
            if not request.user.is_superuser and not is_assigned:
                messages.error(request, "You are not authorized to update this ticket. It is not assigned to you.")
                return redirect('ticket_detail', ticket_id=ticket_id)

            ticket.status = new_status
            if assignee_id:
                ticket.assigned_to_id = assignee_id
            if location:
                ticket.location = location
            if new_status == 'resolved' and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()
            ticket.save()

            if old_status != new_status:
                TicketNote.objects.create(
                    ticket=ticket, author=request.user,
                    note_type='status_change',
                    content=f'Status changed from {old_status} to {new_status}.',
                    is_internal=True,
                )
            if note_content:
                TicketNote.objects.create(
                    ticket=ticket, author=request.user,
                    note_type='diagnostic', content=note_content,
                )
            messages.success(request, 'Ticket updated successfully.')
            return redirect('ticket_detail', ticket_id=ticket_id)

        elif action == 'escalate':
            # Check permission: Only assigned tech or superuser
            is_assigned = hasattr(request.user, 'technician') and ticket.assigned_to == request.user.technician
            if not request.user.is_superuser and not is_assigned:
                messages.error(request, "You are not authorized to escalate this ticket. It is not assigned to you.")
                return redirect('ticket_detail', ticket_id=ticket_id)

            ticket.priority = 'critical'
            ticket.status = 'received'
            ticket.assigned_to = None
            ticket.save()

            TicketNote.objects.create(
                ticket=ticket, author=request.user,
                note_type='escalation',
                content='Ticket escalated to supervisor. Priority upgraded to critical and assignment cleared.',
                is_internal=True,
            )
            messages.warning(request, 'Ticket escalated to supervisor.')
            return redirect('ticket_detail', ticket_id=ticket_id)

        elif action == 'submit_feedback':
            if ticket.status not in ['resolved', 'closed']:
                messages.error(request, 'Cannot submit feedback for open tickets.')
            else:
                ticket.rating = request.POST.get('rating')
                ticket.feedback = request.POST.get('feedback', '')
                ticket.save()
                messages.success(request, 'Thank you for your feedback!')
            return redirect('ticket_detail', ticket_id=ticket_id)

    context = {
        'ticket':      ticket,
        'notes':       notes,
        'technicians': technicians,
        'now':         timezone.now(),
        'active_page': 'tickets',
    }
    return render(request, 'tickets/ticket_detail.html', context)


# ── New Ticket ────────────────────────────────────────────────

@login_required
def ticket_create(request):
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')
    
    technicians = Technician.objects.filter(availability='available')

    if request.method == 'POST':
        ticket = Ticket(
            title=request.POST['title'],
            requester_name=request.POST['requester_name'],
            description=request.POST['description'],
            category=request.POST['category'],
            priority=request.POST['priority'],
            location=request.POST.get('location', ''),
            submitted_by=request.user,
            status='received',
        )
        # Only admin (superuser) can directly assign a technician
        if request.user.is_superuser:
            tech_id = request.POST.get('assigned_to')
            if tech_id:
                ticket.assigned_to_id = tech_id
                ticket.status = 'assigned'
        ticket.save()

        TicketNote.objects.create(
            ticket=ticket, author=request.user,
            note_type='status_change',
            content='Ticket created and received.',
            is_internal=True,
        )
        messages.success(request, f'Ticket {ticket.ticket_id} created successfully.')
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    context = {
        'technicians': technicians,
        'active_page': 'tickets',
        'categories': Ticket.CATEGORY_CHOICES,
        'priorities': Ticket.PRIORITY_CHOICES,
    }
    return render(request, 'tickets/ticket_create.html', context)


# ── Assignments ───────────────────────────────────────────────

@login_required
def assignments(request):
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')
    
    unassigned  = Ticket.objects.filter(assigned_to__isnull=True,
                                        status__in=['received', 'triaged']).order_by('created_at')
    technicians = Technician.objects.all()

    if request.method == 'POST':
        ticket_id  = request.POST.get('ticket_id')
        tech_id    = request.POST.get('technician_id')
        ticket     = get_object_or_404(Ticket, id=ticket_id)
        technician = get_object_or_404(Technician, id=tech_id)
        ticket.assigned_to = technician
        ticket.status = 'assigned'
        ticket.save()
        TicketNote.objects.create(
            ticket=ticket, author=request.user,
            note_type='status_change',
            content=f'Assigned to {technician.name}.',
            is_internal=True,
        )
        messages.success(request, f'{ticket.ticket_id} assigned to {technician.name}.')
        return redirect('assignments')

    context = {
        'unassigned':  unassigned,
        'technicians': technicians,
        'active_page': 'assign',
    }
    return render(request, 'tickets/assignments.html', context)


# ── Reports ───────────────────────────────────────────────────

@login_required
def reports(request):
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')
    
    now  = timezone.now()
    freq = request.GET.get('period', 'weekly')

    if freq == 'daily':
        start = now - timedelta(days=1)
    elif freq == 'monthly':
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=7)

    qs = Ticket.objects.filter(created_at__gte=start)
    open_statuses = ['received', 'triaged', 'assigned', 'in_progress']

    received  = qs.count()
    resolved  = qs.filter(status__in=['resolved', 'closed']).count()
    breaches  = qs.filter(status__in=open_statuses, sla_due_at__lt=now).count()
    sla_rate  = round((resolved / received * 100) if received else 0)

    resolved_with_time = qs.filter(resolved_at__isnull=False)
    avg_secs = 0
    if resolved_with_time.exists():
        total_secs = sum(
            (t.resolved_at - t.created_at).total_seconds()
            for t in resolved_with_time
            if t.resolved_at and t.created_at
        )
        avg_secs = total_secs / resolved_with_time.count()
    avg_hours = round(avg_secs / 3600, 1)

    by_category = (
        qs.values('category')
          .annotate(count=Count('id'))
          .order_by('-count')
    )
    by_priority = (
        qs.values('priority')
          .annotate(count=Count('id'))
          .order_by('-count')
    )

    tech_stats = []
    for tech in Technician.objects.all():
        tq = qs.filter(assigned_to=tech)
        t_resolved = tq.filter(status__in=['resolved', 'closed'])
        t_assigned = tq.count()
        t_res_count = t_resolved.count()
        t_sla_rate = round((t_res_count / t_assigned * 100) if t_assigned else 0)
        t_breaches = tq.filter(status__in=open_statuses, sla_due_at__lt=now).count()

        t_avg_hrs = 0
        t_resolved_time = t_resolved.filter(resolved_at__isnull=False)
        if t_resolved_time.exists():
            t_secs = sum(
                (t.resolved_at - t.created_at).total_seconds()
                for t in t_resolved_time
                if t.resolved_at and t.created_at
            )
            t_avg_hrs = round(t_secs / 3600 / t_resolved_time.count(), 1)

        tech_stats.append({
            'tech':      tech,
            'assigned':  t_assigned,
            'resolved':  t_res_count,
            'avg_hours': t_avg_hrs,
            'sla_rate':  t_sla_rate,
            'breaches':  t_breaches,
        })

    schedules = ReportSchedule.objects.all()

    context = {
        'received':    received,
        'resolved':    resolved,
        'sla_rate':    sla_rate,
        'breaches':    breaches,
        'avg_hours':   avg_hours,
        'by_category': list(by_category),
        'by_priority': list(by_priority),
        'tech_stats':  tech_stats,
        'schedules':   schedules,
        'period':      freq,
        'active_page': 'reports',
    }
    return render(request, 'tickets/reports.html', context)


# ── Technicians ───────────────────────────────────────────────

@login_required
def technician_list(request):
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return redirect('index')
    
    technicians = Technician.objects.all()
    context = {
        'technicians': technicians,
        'active_page': 'technicians',
    }
    return render(request, 'tickets/technician_list.html', context)


# ── API: Quick assign (AJAX) ──────────────────────────────────

@login_required
@require_POST
def api_assign(request):
    data    = json.loads(request.body)
    ticket  = get_object_or_404(Ticket, id=data['ticket_id'])
    tech    = get_object_or_404(Technician, id=data['tech_id'])
    ticket.assigned_to = tech
    ticket.status = 'assigned'
    ticket.save()
    TicketNote.objects.create(
        ticket=ticket, author=request.user,
        note_type='status_change',
        content=f'Assigned to {tech.name} via quick-assign.',
        is_internal=True,
    )
    return JsonResponse({'ok': True, 'message': f'Assigned to {tech.name}'})


@login_required
def api_notification_check(request):
    """
    Checks for new, unassigned tickets. 
    Returns the current count of 'received' tickets that are not assigned.
    """
    if not request.user.is_superuser:
        return JsonResponse({'count': 0})
    
    count = Ticket.objects.filter(status='received', assigned_to__isnull=True).count()
    return JsonResponse({'received_unassigned_count': count})


# ── Queue Public API ──────────────────────────────────────────

def api_queue_status(request):
    """Returns live queue status as JSON for real-time polling."""
    serving = Ticket.objects.filter(status='in_progress').order_by('-updated_at').first()
    waiting = Ticket.objects.filter(status='received').order_by('created_at')

    return JsonResponse({
        'serving': {
            'ticket_id': serving.ticket_id,
            'name': serving.requester_name,
            'title': serving.title,
            'dept': serving.location or '',
            'category': serving.get_category_display(),
            'priority': serving.priority,
        } if serving else None,
        'waiting': [
            {
                'ticket_id': t.ticket_id,
                'name': t.requester_name,
                'title': t.title,
                'dept': t.location or '',
                'category': t.get_category_display(),
                'priority': t.priority,
            }
            for t in waiting
        ],
        'waiting_count': waiting.count(),
    })


@require_POST
def api_queue_join(request):
    """AJAX endpoint for joining the queue without login."""
    try:
        data = request.POST
        name = data.get('requester_name', '').strip()
        if not name:
            return JsonResponse({'ok': False, 'error': 'Name is required.'})

        issue_title = data.get('title', '').strip()
        asset_tag   = data.get('asset_tag', '').strip()
        location    = data.get('location', '').strip()
        # Combine location + asset tag for the location field
        if asset_tag and location:
            loc_combined = f"{location} / {asset_tag}"
        elif asset_tag:
            loc_combined = asset_tag
        else:
            loc_combined = location

        ticket = Ticket.objects.create(
            title=issue_title or f"Repair request from {name}",
            requester_name=name,
            description=data.get('description', ''),
            category=data.get('category', 'other'),
            priority=data.get('priority', 'medium'),
            location=loc_combined,
            submitted_by=None,
            status='received',
        )
        TicketNote.objects.create(
            ticket=ticket,
            note_type='status_change',
            content='Joined queue via public form.',
            is_internal=True,
        )
        # Calculate position
        position = Ticket.objects.filter(
            status='received', created_at__lte=ticket.created_at
        ).count()

        return JsonResponse({
            'ok': True,
            'ticket_id': ticket.ticket_id,
            'position': position,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@require_POST
def api_queue_leave(request):
    """AJAX endpoint for leaving the queue."""
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        ticket = Ticket.objects.filter(ticket_id=ticket_id, status='received').first()
        if ticket:
            ticket.status = 'closed'
            ticket.save()
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Ticket not found or already served.'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ── Queue Admin API ───────────────────────────────────────────


@login_required
@require_POST
def api_queue_next(request):
    """Admin: call the next person in queue."""
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'})

    # Finish any currently in-progress tickets first
    Ticket.objects.filter(status='in_progress').update(
        status='in_progress'  # keep, don't auto-close
    )
    next_ticket = Ticket.objects.filter(status='received').order_by('created_at').first()
    if not next_ticket:
        return JsonResponse({'ok': False, 'error': 'No one in the queue.'})

    next_ticket.status = 'in_progress'
    next_ticket.save()
    TicketNote.objects.create(
        ticket=next_ticket, author=request.user,
        note_type='status_change',
        content=f'Called to be served by {request.user.get_full_name() or request.user.username}.',
        is_internal=True,
    )
    return JsonResponse({'ok': True, 'ticket_id': next_ticket.ticket_id})


@login_required
@require_POST
def api_queue_resolve(request):
    """Admin: mark currently serving ticket as resolved."""
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'})
    try:
        data = json.loads(request.body)
        ticket = get_object_or_404(Ticket, ticket_id=data.get('ticket_id'))
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        TicketNote.objects.create(
            ticket=ticket, author=request.user,
            note_type='status_change',
            content='Issue resolved.',
            is_internal=False,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_POST
def api_queue_skip(request):
    """Admin: skip the current ticket (move to back of queue)."""
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'})
    try:
        data = json.loads(request.body)
        ticket = get_object_or_404(Ticket, ticket_id=data.get('ticket_id'))
        ticket.status = 'received'
        ticket.save()
        TicketNote.objects.create(
            ticket=ticket, author=request.user,
            note_type='status_change',
            content='Ticket skipped back to queue.',
            is_internal=True,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_POST
def api_queue_serve(request):
    """Admin: serve a specific ticket from the waiting list."""
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'})
    try:
        data = json.loads(request.body)
        ticket = get_object_or_404(Ticket, ticket_id=data.get('ticket_id'))
        ticket.status = 'in_progress'
        ticket.save()
        TicketNote.objects.create(
            ticket=ticket, author=request.user,
            note_type='status_change',
            content=f'Directly served by {request.user.get_full_name() or request.user.username}.',
            is_internal=True,
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_POST
def api_queue_remove(request):
    """Admin: remove a person from the queue entirely."""
    if not request.user.is_staff and not hasattr(request.user, 'technician'):
        return JsonResponse({'ok': False, 'error': 'Permission denied.'})
    try:
        data = json.loads(request.body)
        ticket = get_object_or_404(Ticket, ticket_id=data.get('ticket_id'))
        ticket.status = 'closed'
        ticket.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ── Rate Technician API ──────────────────────────────────────

@login_required
@require_POST
def api_rate_technician(request, tech_id):
    """Superuser-only: submit a 1–5 star rating for a technician.
    Attaches the rating to their most recent resolved/closed ticket.
    If no such ticket exists, returns an error.
    """
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Only admins can rate technicians.'})
    try:
        data = json.loads(request.body)
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '').strip()
        if not 1 <= rating <= 5:
            return JsonResponse({'ok': False, 'error': 'Rating must be between 1 and 5.'})

        tech = get_object_or_404(Technician, id=tech_id)

        # Prefer an unrated resolved ticket; fall back to latest resolved ticket
        ticket = (
            tech.ticket_set.filter(status__in=['resolved', 'closed'], rating__isnull=True)
            .order_by('-resolved_at')
            .first()
        )
        if not ticket:
            ticket = (
                tech.ticket_set.filter(status__in=['resolved', 'closed'])
                .order_by('-resolved_at')
                .first()
            )
        if not ticket:
            return JsonResponse({'ok': False, 'error': f'{tech.name} has no resolved tickets to rate.'})

        ticket.rating = rating
        if comment:
            ticket.feedback = comment
        ticket.save()

        if comment:
            TicketNote.objects.create(
                ticket=ticket,
                author=request.user,
                note_type='comment',
                content=f'Admin rating ({rating}★): {comment}',
                is_internal=True,
            )

        return JsonResponse({
            'ok': True,
            'avg_rating': tech.avg_rating,
            'rating_count': tech.rating_count,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})

