from django.core.validators import MinValueValidator
from django.db import models


class Service(models.Model):
    """ZHL-17: шебер ұсынатын қызмет."""
    name = models.CharField('Атауы', max_length=100)
    duration_min = models.PositiveIntegerField('Ұзақтығы, мин', validators=[MinValueValidator(5)])
    price = models.PositiveIntegerField('Бағасы, ₸')
    is_active = models.BooleanField('Белсенді', default=True)

    class Meta:
        verbose_name = 'Қызмет'
        verbose_name_plural = 'Қызметтер'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.duration_min} мин, {self.price} ₸'

