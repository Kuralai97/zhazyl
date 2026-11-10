"""Тестілік деректер генераторы (11-ЗЖ). Нақты дербес деректер жоқ.

Зерно бекітілген: бірдей --seed әрқашан бірдей деректер береді, сондықтан
табылған ақау кез келген адамда қайталанады.
    python manage.py demo_derekter --seed 42
"""
import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Booking, Service, WorkingHours

NAMES = ['Тест Клиент', 'Сынақ Пайдаланушы', 'Демо Адам', 'Үлгі Клиент']
SERVICES = ['Шаш алу', 'Сақал түзету', 'Шаш + сақал', 'Балалар шашы', 'Машинамен алу']


class Command(BaseCommand):
    help = 'Тестілік деректер: 50 қызмет, жұмыс кестесі, 300 жазылу (ФЕТ-01 шарты)'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--services', type=int, default=50)
        parser.add_argument('--bookings', type=int, default=300)

    def handle(self, *args, **o):
        rnd = random.Random(o['seed'])
        Booking.objects.all().delete()
        Service.objects.all().delete()
        WorkingHours.objects.all().delete()
        for wd in range(6):
            WorkingHours.objects.create(weekday=wd, start=time(10), end=time(20),
                                        break_start=time(14), break_end=time(15))
        WorkingHours.objects.create(weekday=6, is_day_off=True)
        services = [Service.objects.create(name=f'{SERVICES[i % 5]} №{i + 1}',
                                           duration_min=rnd.choice([30, 30, 60]),
                                           price=rnd.choice([3000, 5000, 6000, 8000]))
                    for i in range(o['services'])]
        tz = timezone.get_current_timezone()
        start_day = timezone.localdate() - timedelta(days=30)
        made = 0
        while made < o['bookings']:
            day = start_day + timedelta(days=rnd.randint(0, 59))
            if day.weekday() == 6:
                continue
            t = timezone.make_aware(datetime.combine(day, time(rnd.choice([10, 11, 12, 13, 15, 16, 17, 18]),
                                                               rnd.choice([0, 30]))), tz)
            b = Booking(client_name=f'{rnd.choice(NAMES)} {made + 1}',
                        client_phone=f'+7700{rnd.randint(0, 9999999):07d}',
                        service=rnd.choice(services), start=t, consent=True,
                        source=rnd.choice(['online', 'phone']),
                        status='done' if day < timezone.localdate() else 'new')
            try:
                b.full_clean()
            except Exception:
                continue
            b.save()
            made += 1
        self.stdout.write(f'Дайын: {len(services)} қызмет, {made} жазылу, seed={o["seed"]}')
