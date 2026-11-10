from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm
from .models import Booking, Service
from .slots import free_slots


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
    days = [today + timedelta(days=i) for i in range(14)]
    return render(request, 'booking/book.html', {
        'service': service, 'day': day, 'days': days, 'slots': free_slots(service, day), 'form': form,
    })


def done(request):
    """Жазылу расталды. Тек осы браузерде жасалған жазылу көрінеді."""
    pk = request.session.get('last_booking')
    if not pk:
        raise Http404('Жазылу табылмады')
    return render(request, 'booking/done.html', {'b': get_object_or_404(Booking, pk=pk)})
