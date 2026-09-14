from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_backend, name='test_backend'),

    # Public / marketing pages
    path('', views.public_home, name='public_home'),
    path('login/', views.public_login, name='public_login'),
    path('get-started/', views.public_get_started, name='public_get_started'),
]

