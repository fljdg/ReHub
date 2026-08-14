from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_backend, name='test_backend'),
]
