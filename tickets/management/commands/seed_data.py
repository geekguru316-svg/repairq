from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from tickets.models import Ticket, Technician, TechnicianSkill, TicketNote, ReportSchedule


class Command(BaseCommand):
    help = 'Seed the database with demo data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')

        # Admin user
        admin, _ = User.objects.get_or_create(username='admin')
        admin.set_password('admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.first_name = 'Maria'
        admin.last_name = 'Alcantara'
        admin.save()

        # Regular users
        users = {}
        for uname, fname, lname in [
            ('rico', 'Rico', 'Domingo'),
            ('ana', 'Ana', 'Cruz'),
            ('miguel', 'Miguel', 'Santos'),
            ('linda', 'Linda', 'Reyes'),
        ]:
            u, _ = User.objects.get_or_create(username=uname)
            u.set_password('password')
            u.first_name = fname
            u.last_name = lname
            u.save()
            users[uname] = u

        # Technicians
        techs_data = [
            ('Joel Reyes',  'joel.reyes@company.com',  'Infrastructure', 'available', '#3b82f6',
             ['hardware', 'network']),
            ('Sara Lim',    'sara.lim@company.com',    'IT Support',     'busy',      '#7c3aed',
             ['network', 'software']),
            ('Ben Mateo',   'ben.mateo@company.com',   'IT Support',     'available', '#059669',
             ['hardware', 'network']),
            ('Aida Kwan',   'aida.kwan@company.com',   'Security',       'busy',      '#dc2626',
             ['security', 'network']),
            ('Dan Garcia',  'dan.garcia@company.com',  'IT Support',     'available', '#ca8a04',
             ['hardware', 'software']),
            ('Nina Perez',  'nina.perez@company.com',  'IT Support',     'off',       '#475569',
             ['software']),
        ]

        techs = {}
        for name, email, dept, avail, color, skills in techs_data:
            t, _ = Technician.objects.get_or_create(email=email, defaults={
                'name': name, 'department': dept,
                'availability': avail, 'color': color,
            })
            t.name = name; t.availability = avail; t.color = color
            t.save()
            TechnicianSkill.objects.filter(technician=t).delete()
            for skill in skills:
                TechnicianSkill.objects.create(technician=t, skill=skill)
            techs[name] = t

        now = timezone.now()

        # Sample tickets
        tickets_data = [
            ('Server room AC failure',          'The air conditioning unit in Server Room B1 stopped functioning at approximately 09:30. Room temperature rising rapidly. Current reading is 32°C and climbing. Critical systems at risk of thermal shutdown.',
             'critical', 'hardware', 'in_progress', techs['Joel Reyes'],   now - timedelta(hours=2),  now - timedelta(hours=2) + timedelta(hours=4),  users['rico']),
            ('Network printer offline — Floor 3','The shared printer on Floor 3 (HP LaserJet Pro) is offline. Users cannot print documents. Printer shows error code E04 on display.',
             'high',     'network',  'assigned',    techs['Ben Mateo'],    now - timedelta(hours=3),  now - timedelta(hours=3) + timedelta(hours=8),  users['ana']),
            ('Laptop screen cracked — R. Santos','Laptop screen cracked after it was accidentally dropped. Device still boots but display is unusable. Asset tag: LT-2045.',
             'medium',   'hardware', 'received',    None,                  now - timedelta(hours=4),  now - timedelta(hours=4) + timedelta(hours=48), users['rico']),
            ('VPN authentication error',         'Unable to authenticate to corporate VPN after password reset. Receiving error: "Authentication failed - credentials invalid". Affects remote work.',
             'high',     'software', 'in_progress', techs['Sara Lim'],    now - timedelta(hours=5),  now - timedelta(hours=5) + timedelta(hours=8),  users['miguel']),
            ('Email quota exceeded',             'User mailbox has exceeded the 10GB quota. Unable to send or receive emails. Requesting quota increase or archive assistance.',
             'low',      'software', 'resolved',    techs['Dan Garcia'],  now - timedelta(hours=6),  now - timedelta(hours=6) + timedelta(hours=120), users['linda']),
            ('Mouse not detected on startup',    'Wireless mouse not detected on PC startup. Tried different USB port and new batteries. Issue persists.',
             'low',      'hardware', 'triaged',     None,                  now - timedelta(hours=7),  now - timedelta(hours=7) + timedelta(hours=120), users['ana']),
            ('Database connection timeout',      'Production database returning connection timeouts intermittently. Affecting 3 internal applications. Started around 08:00 today.',
             'critical', 'network',  'in_progress', techs['Aida Kwan'],   now - timedelta(days=1),   now - timedelta(days=1) + timedelta(hours=4),   users['rico']),
            ('Projector HDMI port damaged',      'HDMI port on Boardroom projector physically damaged. Cannot connect laptops for presentations. Asset tag: PR-0012.',
             'medium',   'hardware', 'received',    None,                  now - timedelta(hours=12), now - timedelta(hours=12) + timedelta(hours=48), users['miguel']),
            ('Antivirus definitions outdated',   'Security scan flagging that antivirus definitions are 14 days out of date on 12 workstations. Auto-update appears to have failed.',
             'high',     'security', 'assigned',    techs['Aida Kwan'],   now - timedelta(hours=10), now - timedelta(hours=10) + timedelta(hours=8),  users['linda']),
            ('Windows update failure',           'Workstation failing to install latest Windows security patches. Update fails at 87% with error code 0x80070057.',
             'medium',   'software', 'resolved',    techs['Sara Lim'],    now - timedelta(days=2),   now - timedelta(days=2) + timedelta(hours=48),  users['rico']),
        ]

        for title, desc, pri, cat, status, tech, created, sla_due, user in tickets_data:
            if Ticket.objects.filter(title=title).exists():
                continue
            t = Ticket(
                title=title, description=desc, priority=pri, category=cat,
                status=status, assigned_to=tech, submitted_by=user,
                sla_due_at=sla_due,
            )
            t.save()
            t.created_at = created
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

        # Report schedules
        for name, freq in [('Daily Queue Digest', 'daily'), ('Weekly Performance', 'weekly'), ('Monthly Executive Summary', 'monthly')]:
            ReportSchedule.objects.get_or_create(
                name=name,
                defaults={'frequency': freq, 'recipients': 'admin@company.com', 'format': 'pdf', 'created_by': admin}
            )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully!'))
        self.stdout.write('Login: admin / admin')
