from datetime import date, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import BookingForm
from .models import Booking, Service
from .slots import free_slots

WEEKDAYS = ['Дс', 'Сс', 'Ср', 'Бс', 'Жм', 'Сб', 'Жс']
SALT = 'zhazylu-basqaru'


def manage_link(request, booking):
    """Клиенттің жеке сілтемесі: қол қойылған токен, дерекқорда сақталмайды."""
    token = signing.dumps(booking.pk, salt=SALT)
    return request.build_absolute_uri(reverse('booking:manage', args=[token]))


def index(request):
    """ZHL-20: қызметтер тізімі бағасымен."""
    return render(request, 'booking/index.html', {'services': Service.objects.filter(is_active=True)})


def book(request, service_id):
    """ZHL-10, ZHL-21: күнді, бос уақытты таңдап жазылу."""
    service = get_object_or_404(Service, pk=service_id, is_active=True)
    today = timezone.localdate()
    try:
        day = date.fromisoformat(request.GET.get('kun', '')) if request.GET.get('kun') else today
    except ValueError:
        day = today
    day = min(max(day, today), today + timedelta(days=30))
    form = BookingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        b = Booking(service=service, source='online', **form.cleaned_data)
        try:
            with transaction.atomic():
                b.full_clean()
                if b.start not in free_slots(service, timezone.localtime(b.start).date()):
                    raise ValidationError('Бұл уақыт бос емес. Басқа уақытты таңдаңыз.')
                b.save()
        except ValidationError as e:
            form.add_error(None, e.messages[0])
        else:
            request.session['last_booking'] = b.pk
            return redirect('booking:done')
        day = timezone.localtime(form.cleaned_data['start']).date()
    days = [{'d': today + timedelta(days=i), 'wd': WEEKDAYS[(today + timedelta(days=i)).weekday()]} for i in range(14)]
    return render(request, 'booking/book.html', {
        'service': service, 'day': day, 'days': days, 'slots': free_slots(service, day), 'form': form,
    })


def done(request):
    """Жазылу расталды. Тек осы браузерде жасалған жазылу көрінеді."""
    pk = request.session.get('last_booking')
    if not pk:
        raise Http404('Жазылу табылмады')
    b = get_object_or_404(Booking, pk=pk)
    return render(request, 'booking/done.html', {'b': b, 'link': manage_link(request, b)})


def manage(request, token):
    """Клиент өз жазылуын жеке сілтеме арқылы көреді және бас тарта алады."""
    try:
        pk = signing.loads(token, salt=SALT)
    except signing.BadSignature:
        raise Http404('Сілтеме жарамсыз')
    b = get_object_or_404(Booking, pk=pk)
    can_cancel = b.status == 'new' and b.start > timezone.now()
    if request.method == 'POST' and can_cancel:
        b.status = 'cancelled'
        b.save(update_fields=['status'])
        can_cancel = False
    return render(request, 'booking/manage.html', {'b': b, 'can_cancel': can_cancel})


@staff_member_required
def schedule(request):
    """Иесінің күндік кестесі: кім, қашан, қандай қызмет; статусты бір басумен белгілеу."""
    today = timezone.localdate()
    try:
        day = date.fromisoformat(request.GET.get('kun', '')) if request.GET.get('kun') else today
    except ValueError:
        day = today
    if request.method == 'POST' and request.POST.get('status') in ('done', 'no_show', 'new'):
        Booking.objects.filter(pk=request.POST.get('id')).update(status=request.POST['status'])
        return redirect(f"{reverse('booking:schedule')}?kun={day.isoformat()}")
    items = list(Booking.objects.filter(start__date=day).select_related('service').order_by('start'))
    active = [b for b in items if b.status != 'cancelled']
    return render(request, 'booking/schedule.html', {
        'day': day, 'wd': WEEKDAYS[day.weekday()], 'items': items,
        'prev': day - timedelta(days=1), 'next': day + timedelta(days=1), 'today': today,
        'count': len(active), 'revenue': sum(b.service.price for b in active),
        'done': sum(b.status == 'done' for b in items), 'no_show': sum(b.status == 'no_show' for b in items),
        'cancelled': sum(b.status == 'cancelled' for b in items),
    })
