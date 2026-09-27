from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('get-started/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('research/', views.research, name='research'),
    path('assistant/', views.assistant, name='assistant'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', views.profile, name='profile'),
    path('search/', views.search, name='search'),
]