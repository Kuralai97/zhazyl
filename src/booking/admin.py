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
