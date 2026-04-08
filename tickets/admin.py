from django.contrib import admin
from .models import Ticket, Technician, TechnicianSkill, TicketNote, ReportSchedule


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'title', 'status', 'priority', 'category', 'assigned_to', 'created_at', 'overdue_status')
    list_filter  = ('status', 'priority', 'category')
    search_fields = ('ticket_id', 'title', 'description')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')

    @admin.display(boolean=True, description='Overdue')
    def overdue_status(self, obj):
        try:
            return obj.is_overdue
        except Exception:
            return False


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'availability', 'open_ticket_count')


@admin.register(TicketNote)
class TicketNoteAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'note_type', 'created_at', 'is_internal')
    list_filter  = ('note_type', 'is_internal')


admin.site.register(TechnicianSkill)
admin.site.register(ReportSchedule)
