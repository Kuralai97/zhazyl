from django.urls import path

from . import views

app_name = 'booking'
urlpatterns = [
    path('', views.index, name='index'),
    path('zhazylu/<int:service_id>/', views.book, name='book'),
    path('dayin/', views.done, name='done'),
    path('zhazylu/basqaru/<str:token>/', views.manage, name='manage'),
    path('iesi/keste/', views.schedule, name='schedule'),
]
