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


class WorkingHours(models.Model):
    """ZHL-13: аптаның әр күніндегі жұмыс уақыты."""
    WEEKDAYS = [(0, 'Дүйсенбі'), (1, 'Сейсенбі'), (2, 'Сәрсенбі'), (3, 'Бейсенбі'),
                (4, 'Жұма'), (5, 'Сенбі'), (6, 'Жексенбі')]
    weekday = models.PositiveSmallIntegerField('Күн', choices=WEEKDAYS, unique=True)
    is_day_off = models.BooleanField('Демалыс', default=False)
    start = models.TimeField('Басталуы', null=True, blank=True)
    end = models.TimeField('Аяқталуы', null=True, blank=True)
    break_start = models.TimeField('Үзіліс басы', null=True, blank=True)
    break_end = models.TimeField('Үзіліс соңы', null=True, blank=True)

    class Meta:
        verbose_name = 'Жұмыс күні'
        verbose_name_plural = 'Жұмыс кестесі'
        ordering = ['weekday']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_day_off:
            return
        if not self.start or not self.end or self.start >= self.end:
            raise ValidationError('Жұмыс уақытының басы аяғынан ерте болуы керек.')
        if bool(self.break_start) != bool(self.break_end):
            raise ValidationError('Үзілістің басы мен соңы екеуі де толтырылуы керек.')
        if self.break_start and not (self.start <= self.break_start < self.break_end <= self.end):
            raise ValidationError('Үзіліс жұмыс уақытының ішінде болуы керек.')

    def __str__(self):
        if self.is_day_off:
            return f'{self.get_weekday_display()}: демалыс'
        return f'{self.get_weekday_display()}: {self.start:%H:%M}–{self.end:%H:%M}'
