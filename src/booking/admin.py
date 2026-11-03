from django.contrib import admin

from .models import Booking, Service, WorkingHours


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_min', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ('weekday', 'is_day_off', 'start', 'end', 'break_start', 'break_end')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('start', 'client_name', 'client_phone', 'service', 'status', 'source')
    list_filter = ('status', 'source', 'start')
    date_hierarchy = 'start'
    search_fields = ('client_name', 'client_phone')
    actions = ['mark_done', 'mark_no_show']

    @admin.action(description='«Өтті» деп белгілеу')
    def mark_done(self, request, queryset):
        queryset.update(status='done')

    @admin.action(description='«Келмей қалды» деп белгілеу')
    def mark_no_show(self, request, queryset):
        queryset.update(status='no_show')
