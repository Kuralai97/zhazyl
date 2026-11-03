from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Service


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

