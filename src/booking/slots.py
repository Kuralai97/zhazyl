"""ZHL-10: таңдалған күнге бос уақыттарды есептеу."""
from datetime import datetime, timedelta

from django.utils import timezone

from .models import Booking, WorkingHours

STEP_MIN = 30


def free_slots(service, day, now=None):
    now = now or timezone.now()
    wh = WorkingHours.objects.filter(weekday=day.weekday()).first()
    if not wh or wh.is_day_off or not wh.start or not wh.end:
        return []
    tz = timezone.get_current_timezone()

    def at(t):
        return timezone.make_aware(datetime.combine(day, t), tz)

    start, end = at(wh.start), at(wh.end)
    brk = (at(wh.break_start), at(wh.break_end)) if wh.break_start else None
    dur = timedelta(minutes=service.duration_min)
    busy = [(b.start, b.end) for b in Booking.objects.exclude(status='cancelled')
            .filter(start__date=day).select_related('service')]
    slots, t = [], start
    while t + dur <= end:
        e = t + dur
        free = t > now and not (brk and t < brk[1] and brk[0] < e) \
            and not any(t < be and bs < e for bs, be in busy)
        if free:
            slots.append(t)
        t += timedelta(minutes=STEP_MIN)
    return slots
