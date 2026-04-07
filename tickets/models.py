from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Technician(models.Model):
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('off', 'Off Duty'),
    ]
    SKILL_CHOICES = [
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('network', 'Network'),
        ('security', 'Security'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100, blank=True)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    initials = models.CharField(max_length=3, blank=True)
    color = models.CharField(max_length=7, default='#3b82f6')

    def save(self, *args, **kwargs):
        if not self.initials:
            parts = self.name.split()
            self.initials = ''.join(p[0].upper() for p in parts[:2])
        super().save(*args, **kwargs)

    @property
    def open_ticket_count(self):
        return self.ticket_set.filter(status__in=['received', 'triaged', 'assigned', 'in_progress']).count()

    @property
    def skills_list(self):
        return TechnicianSkill.objects.filter(technician=self).values_list('skill', flat=True)

    @property
    def avg_rating(self):
        """Average star rating (1–5) from all rated tickets assigned to this technician."""
        rated = self.ticket_set.filter(rating__isnull=False)
        count = rated.count()
        if count == 0:
            return None
        total = sum(t.rating for t in rated)
        return round(total / count, 1)

    @property
    def rating_count(self):
        """Number of rated tickets for this technician."""
        return self.ticket_set.filter(rating__isnull=False).count()

    def __str__(self):
        return self.name


class TechnicianSkill(models.Model):
    SKILL_CHOICES = [
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('network', 'Network'),
        ('security', 'Security'),
        ('other', 'Other'),
    ]
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE, related_name='skills')
    skill = models.CharField(max_length=20, choices=SKILL_CHOICES)

    class Meta:
        unique_together = ('technician', 'skill')


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('received',    'Received'),
        ('triaged',     'Triaged'),
        ('assigned',    'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved',    'Resolved'),
        ('closed',      'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low',      'Low'),
        ('medium',   'Medium'),
        ('high',     'High'),
        ('critical', 'Critical'),
    ]
    CATEGORY_CHOICES = [
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('network',  'Network'),
        ('security', 'Security'),
        ('other',    'Other'),
    ]
    SLA_HOURS = {
        'critical': 4,
        'high':     8,
        'medium':   48,
        'low':      120,
    }

    ticket_id   = models.CharField(max_length=30, unique=True, editable=False)
    title       = models.CharField(max_length=200)
    description = models.TextField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='hardware')
    location    = models.CharField(max_length=100, blank=True)
    requester_name = models.CharField(max_length=100, help_text="Name of the person reporting the issue")

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_tickets')
    assigned_to  = models.ForeignKey(Technician, on_delete=models.SET_NULL, null=True, blank=True)

    rating       = models.IntegerField(null=True, blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    feedback     = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)
    closed_at    = models.DateTimeField(null=True, blank=True)
    sla_due_at   = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            from django.utils import timezone
            now = timezone.now()
            date_str = now.strftime('%Y%m%d')
            count = Ticket.objects.filter(ticket_id__startswith=f'TKT-{date_str}').count()
            self.ticket_id = f'TKT-{date_str}-{str(count + 1).zfill(4)}'
        if not self.sla_due_at and self.priority:
            hours = self.SLA_HOURS.get(self.priority, 48)
            from django.utils import timezone
            self.sla_due_at = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.status in ('resolved', 'closed'):
            return False
        return self.sla_due_at and timezone.now() > self.sla_due_at

    @property
    def sla_remaining(self):
        if not self.sla_due_at:
            return None
        return self.sla_due_at - timezone.now()

    @property
    def resolution_time(self):
        if self.resolved_at and self.created_at:
            return self.resolved_at - self.created_at
        return None

    def __str__(self):
        return f'{self.ticket_id} — {self.title}'

    class Meta:
        ordering = ['-created_at']


class TicketNote(models.Model):
    NOTE_TYPE_CHOICES = [
        ('comment',       'Comment'),
        ('diagnostic',    'Diagnostic'),
        ('status_change', 'Status Change'),
        ('escalation',    'Escalation'),
    ]

    ticket    = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='notes')
    author    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default='comment')
    content   = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Note on {self.ticket.ticket_id} by {self.author}'


class ReportSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily',   'Daily'),
        ('weekly',  'Weekly'),
        ('monthly', 'Monthly'),
    ]
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('both', 'Both'),
    ]

    name        = models.CharField(max_length=100)
    frequency   = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    recipients  = models.TextField(help_text='Comma-separated email addresses')
    format      = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf')
    is_active   = models.BooleanField(default=True)
    last_sent   = models.DateTimeField(null=True, blank=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.name} ({self.frequency})'
