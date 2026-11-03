from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Service, WorkingHours


class ServiceTests(TestCase):
    def test_zero_duration_rejected(self):
        s = Service(name='Шаш алу', duration_min=0, price=6000)
        with self.assertRaises(ValidationError):
            s.full_clean()

    def test_valid_service_saved(self):
        s = Service(name='Шаш алу', duration_min=40, price=6000)
        s.full_clean()
        s.save()
        self.assertEqual(Service.objects.count(), 1)


class WorkingHoursTests(TestCase):
    def test_start_after_end_rejected(self):
        w = WorkingHours(weekday=0, start=time(20), end=time(10))
        with self.assertRaises(ValidationError):
            w.full_clean()

    def test_break_outside_hours_rejected(self):
        w = WorkingHours(weekday=0, start=time(10), end=time(20),
                         break_start=time(21), break_end=time(22))
        with self.assertRaises(ValidationError):
            w.full_clean()

    def test_day_off_without_hours_ok(self):
        w = WorkingHours(weekday=6, is_day_off=True)
        w.full_clean()
