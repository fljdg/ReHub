from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('get-started/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
