from django.urls import path
from . import group_views, profile_views, research_views, views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('get-started/', profile_views.signup, name='signup'),
    path('setup-profile/', profile_views.setup_profile, name='setup_profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('research/', research_views.research, name='research'),
    path('research/<int:pk>/', research_views.research_detail, name='research_detail'),
    path('group/', group_views.groups, name='group'),
    path('assistant/', views.assistant, name='assistant'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', profile_views.profile, name='profile'),
    path('search/', views.search, name='search'),
]
