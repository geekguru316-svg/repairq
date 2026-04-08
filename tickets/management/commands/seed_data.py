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

        techs_dict = {}
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
            techs_dict[uname] = tech

        # ── Demo regular users ────────────────────────────────────────────────
        # ── Sample tickets ────────────────────────────────────────────────────
        # Skip creating sample tickets as users may have deleted them and we do not
        # want them recreated on every deployment or service restart.
        
        # tickets_data = [ ... ] 
        # (Demo ticket creation has been removed to prevent them from coming back)

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
