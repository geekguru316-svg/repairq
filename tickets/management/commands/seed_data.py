from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from tickets.models import Ticket, Technician, TechnicianSkill, TicketNote, ReportSchedule


class Command(BaseCommand):
    help = 'Seed the database with demo data and default accounts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')

        # ── Admin user ────────────────────────────────────────────────────────
        admin, _ = User.objects.get_or_create(username='admin')
        admin.set_password('admin123')
        admin.is_staff = True
        admin.is_superuser = True
        admin.first_name = 'Admin'
        admin.last_name = 'User'
        admin.email = 'admin@repairq.com'
        admin.save()

        # ── Real technician Django accounts ───────────────────────────────────
        real_techs = [
            ('jayson',  'Jayson W.',      'Cabradilla', 'jayson.cabradilla@company.com', 'IT Support', '#8b5cf6', 'JC', ['hardware', 'network', 'software']),
            ('arjun',   'Arjun',          'Haincadto',  'geekguru316@gmail.com',         'IT Support', '#f59e0b', 'AH', ['hardware', 'other', 'software']),
            ('allan',   'Engr. Allan C.', 'Abella',     'allan.abella@company.com',      'IT Support', '#10b981', 'AA', ['hardware', 'network', 'security']),
        ]

        for uname, fname, lname, email, dept, color, initials, skills in real_techs:
            # Django user account
            u, _ = User.objects.get_or_create(username=uname)
            u.set_password('tech123')
            u.first_name = fname
            u.last_name = lname
            u.email = email
            u.is_staff = True   # staff access (not superuser)
            u.save()

            # Linked Technician profile
            tech, _ = Technician.objects.get_or_create(email=email, defaults={
                'name': f'{fname} {lname}',
                'department': dept,
                'availability': 'available',
                'color': color,
                'initials': initials,
            })
            tech.name = f'{fname} {lname}'
            tech.user = u
            tech.department = dept
            tech.color = color
            tech.initials = initials
            tech.save()

            TechnicianSkill.objects.filter(technician=tech).delete()
            for skill in skills:
                TechnicianSkill.objects.create(technician=tech, skill=skill)

        # ── Demo regular users ────────────────────────────────────────────────
        users = {}
        for uname, fname, lname in [
            ('rico',   'Rico',   'Domingo'),
            ('ana',    'Ana',    'Cruz'),
            ('miguel', 'Miguel', 'Santos'),
            ('linda',  'Linda',  'Reyes'),
        ]:
            u, _ = User.objects.get_or_create(username=uname)
            u.set_password('password')
            u.first_name = fname
            u.last_name = lname
            u.save()
            users[uname] = u

        # ── Demo additional technicians ───────────────────────────────────────
        demo_techs_data = [
            ('Joel Reyes',  'joel.reyes@repairq.com',  'Infrastructure', 'available', '#ca8a04', ['hardware', 'network']),
            ('Sara Lim',    'sara.lim@repairq.com',    'IT Support',     'busy',      '#dc2626', ['network', 'software']),
            ('Aida Kwan',   'aida.kwan@repairq.com',   'Security',       'busy',      '#475569', ['security', 'network']),
        ]

        demo_techs = {}
        for name, email, dept, avail, color, skills in demo_techs_data:
            t, _ = Technician.objects.get_or_create(email=email, defaults={
                'name': name, 'department': dept,
                'availability': avail, 'color': color,
            })
            t.name = name; t.availability = avail; t.color = color
            t.save()
            TechnicianSkill.objects.filter(technician=t).delete()
            for skill in skills:
                TechnicianSkill.objects.create(technician=t, skill=skill)
            demo_techs[name] = t

        # ── Sample tickets ────────────────────────────────────────────────────
        now = timezone.now()
        tickets_data = [
            ('Server room AC failure',
             'The air conditioning unit in Server Room B1 stopped functioning. Room temperature rising rapidly.',
             'critical', 'hardware', 'in_progress', demo_techs['Joel Reyes'],
             now - timedelta(hours=2), now - timedelta(hours=2) + timedelta(hours=4),
             users['rico'], 'Rico Domingo'),

            ('Network printer offline — Floor 3',
             'The shared printer on Floor 3 is offline. Users cannot print documents.',
             'high', 'network', 'assigned', demo_techs['Joel Reyes'],
             now - timedelta(hours=3), now - timedelta(hours=3) + timedelta(hours=8),
             users['ana'], 'Ana Cruz'),

            ('VPN authentication error',
             'Unable to authenticate to corporate VPN after password reset.',
             'high', 'software', 'in_progress', demo_techs['Sara Lim'],
             now - timedelta(hours=5), now - timedelta(hours=5) + timedelta(hours=8),
             users['miguel'], 'Miguel Santos'),

            ('Database connection timeout',
             'Production database returning connection timeouts intermittently.',
             'critical', 'network', 'in_progress', demo_techs['Aida Kwan'],
             now - timedelta(days=1), now - timedelta(days=1) + timedelta(hours=4),
             users['rico'], 'Rico Domingo'),

            ('Antivirus definitions outdated',
             'Security scan flagging antivirus definitions are 14 days out of date on 12 workstations.',
             'high', 'security', 'assigned', demo_techs['Aida Kwan'],
             now - timedelta(hours=10), now - timedelta(hours=10) + timedelta(hours=8),
             users['linda'], 'Linda Reyes'),
        ]

        for title, desc, pri, cat, status, tech, created, sla_due, user, req_name in tickets_data:
            if Ticket.objects.filter(title=title).exists():
                continue
            t = Ticket(
                title=title, description=desc, priority=pri, category=cat,
                status=status, assigned_to=tech, submitted_by=user,
                sla_due_at=sla_due, requester_name=req_name,
            )
            t.save()
            if status in ('resolved', 'closed'):
                t.resolved_at = created + timedelta(hours=3)
            Ticket.objects.filter(pk=t.pk).update(created_at=created, resolved_at=t.resolved_at)

            TicketNote.objects.create(
                ticket=t, author=admin, note_type='status_change',
                content='Ticket created and received.', is_internal=True,
            )
            if tech:
                TicketNote.objects.create(
                    ticket=t, author=admin, note_type='status_change',
                    content=f'Assigned to {tech.name}.', is_internal=True,
                )

        # ── Report schedules ──────────────────────────────────────────────────
        for name, freq in [
            ('Daily Queue Digest', 'daily'),
            ('Weekly Performance', 'weekly'),
            ('Monthly Executive Summary', 'monthly'),
        ]:
            ReportSchedule.objects.get_or_create(
                name=name,
                defaults={'frequency': freq, 'recipients': 'admin@repairq.com',
                          'format': 'pdf', 'created_by': admin}
            )

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))
        self.stdout.write('─' * 40)
        self.stdout.write('🔑 LOGIN CREDENTIALS:')
        self.stdout.write('  Admin   → username: admin   | password: admin123')
        self.stdout.write('  Jayson  → username: jayson  | password: tech123')
        self.stdout.write('  Arjun   → username: arjun   | password: tech123')
        self.stdout.write('  Allan   → username: allan   | password: tech123')
        self.stdout.write('─' * 40)
