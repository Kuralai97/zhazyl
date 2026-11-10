import re

from django import forms

PHONE = re.compile(r'^\+7\d{10}$')


class BookingForm(forms.Form):
    start = forms.DateTimeField(widget=forms.HiddenInput, error_messages={'required': 'Уақытты таңдаңыз.'})
    client_name = forms.CharField(label='Атыңыз', max_length=100,
                                  error_messages={'required': 'Атыңызды жазыңыз.'})
    client_phone = forms.CharField(label='Телефон (+7XXXXXXXXXX)', max_length=12,
                                   error_messages={'required': 'Телефон нөміріңізді жазыңыз.'})
    consent = forms.BooleanField(label='Атым мен телефонымның жазылу үшін өңделуіне келісемін',
                                 error_messages={'required': 'Жазылу үшін келісім қажет.'})

    def clean_client_phone(self):
        phone = self.cleaned_data['client_phone'].replace(' ', '')
        if not PHONE.match(phone):
            raise forms.ValidationError('Телефон +7XXXXXXXXXX түрінде болуы керек, мысалы +77011234567.')
        return phone
