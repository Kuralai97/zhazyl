from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Booking, Service, WorkingHours


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


class BookingTests(TestCase):
    def setUp(self):
        from datetime import datetime
        from django.utils import timezone
        self.svc = Service.objects.create(name='Шаш алу', duration_min=40, price=6000)
        self.t = timezone.make_aware(datetime(2026, 11, 10, 12, 0))

    def make(self, minutes=0, consent=True):
        from datetime import timedelta
        from .models import Booking
        return Booking(client_name='Дәурен', client_phone='+77000000000', service=self.svc,
                       start=self.t + timedelta(minutes=minutes), consent=consent)

    def test_overlap_rejected(self):
        self.make().save()
        with self.assertRaises(ValidationError):
            self.make(minutes=20).full_clean()

    def test_next_slot_ok(self):
        self.make().save()
        self.make(minutes=40).full_clean()

    def test_consent_required(self):
        with self.assertRaises(ValidationError):
            self.make(consent=False).full_clean()

    def test_cancelled_frees_slot(self):
        b = self.make()
        b.status = 'cancelled'
        b.save()
        self.make(minutes=10).full_clean()


class PublicPagesTests(TestCase):
    """ZHL-20, ZHL-10, ZHL-21 және ФЕТ-06, ФЕТ-10 (интеграциялық тесттер)."""

    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone
        self.svc = Service.objects.create(name='Шаш алу', duration_min=30, price=6000)
        self.day = timezone.localdate() + timedelta(days=1)
        if self.day.weekday() == 6:
            self.day += timedelta(days=1)
        WorkingHours.objects.create(weekday=self.day.weekday(), start=time(10), end=time(12),
                                    break_start=time(11), break_end=time(11, 30))

    def slots(self):
        from .slots import free_slots
        return free_slots(self.svc, self.day)

    def post(self, **kw):
        data = {'start': self.slots()[0].isoformat(), 'client_name': 'Тест',
                'client_phone': '+77011234567', 'consent': 'on'}
        data.update(kw)
        return self.client.post(f'/zhazylu/{self.svc.pk}/?kun={self.day.isoformat()}', data)

    def test_index_lists_services(self):
        r = self.client.get('/')
        self.assertContains(r, 'Шаш алу')
        self.assertContains(r, '6000 ₸')

    def test_index_empty_message(self):
        Service.objects.all().delete()
        self.assertContains(self.client.get('/'), 'Қызметтер әзірге қосылмаған')

    def test_slots_skip_break(self):
        self.assertEqual([t.strftime('%H:%M') for t in self.slots()], ['10:00', '10:30', '11:30'])

    def test_booking_created_and_slot_taken(self):
        r = self.post()
        self.assertRedirects(r, '/dayin/')
        self.assertEqual(Booking.objects.get().source, 'online')
        self.assertNotIn('10:00', [t.strftime('%H:%M') for t in self.slots()])

    def test_taken_slot_rejected(self):
        first = self.slots()[0].isoformat()
        self.post()
        r = self.post(start=first)
        self.assertContains(r, 'бос емес')
        self.assertEqual(Booking.objects.count(), 1)

    def test_without_consent_rejected(self):
        r = self.post(consent='')
        self.assertContains(r, 'келісім қажет')
        self.assertEqual(Booking.objects.count(), 0)

    def test_bad_phone_keeps_entered_name(self):
        r = self.post(client_phone='8701', client_name='Айгерім')
        self.assertContains(r, '+7XXXXXXXXXX')
        self.assertContains(r, 'Айгерім')

    def test_done_page_not_visible_in_other_browser(self):
        self.post()
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/dayin/').status_code, 404)

    def test_admin_calendar_requires_login(self):
        r = self.client.get('/admin/booking/booking/')
        self.assertEqual(r.status_code, 302)


class DemoDataTests(TestCase):
    def test_same_seed_same_data(self):
        from django.core.management import call_command
        call_command('demo_derekter', seed=7, services=5, bookings=20, stdout=open('/dev/null', 'w'))
        a = list(Booking.objects.values_list('client_phone', flat=True))
        call_command('demo_derekter', seed=7, services=5, bookings=20, stdout=open('/dev/null', 'w'))
        self.assertEqual(a, list(Booking.objects.values_list('client_phone', flat=True)))
