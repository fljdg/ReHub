from django.urls import path
from .legal_views import terms
from . import group_views, otp_views, profile_views, research_views, views

app_name = 'core'

urlpatterns = [
    path('terms/', terms, name='terms'),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', otp_views.verify_otp, name='verify_otp'),
    path('verify-otp/resend/', otp_views.resend_otp, name='resend_otp'),
    path('get-started/', profile_views.signup, name='signup'),
    path('setup-profile/', profile_views.setup_profile, name='setup_profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('research/', research_views.research, name='research'),
    path('research/<int:pk>/', research_views.research_detail, name='research_detail'),
    path('research/', research_views.research, name='research'),
    path('research/<int:pk>/', research_views.research_detail, name='research_detail'),
    path('research/<int:pk>/tab/<int:apk>/submit/', research_views.tab_submit, name='tab_submit'),
    path('research/', research_views.research, name='research'),
    path('research/<int:pk>/', research_views.research_detail, name='research_detail'),
    path('research/<int:pk>/tab/<int:apk>/submit/', research_views.tab_submit, name='tab_submit'),
    path('research/<int:pk>/plan/', research_views.plan_setup, name='plan_setup'),
    path('research/<int:pk>/tab/add/', research_views.tab_add, name='tab_add'),
    path('research/<int:pk>/tab/<int:apk>/edit/', research_views.tab_edit, name='tab_edit'),
    path('research/<int:pk>/tab/<int:apk>/delete/', research_views.tab_delete, name='tab_delete'),
    path('submission/<int:pk>/download/', research_views.submission_download, name='submission_download'),
    path('submission/<int:pk>/review/', research_views.submission_review, name='submission_review'),
    path('submission/<int:pk>/download/', research_views.submission_download, name='submission_download'),
    path('group/', group_views.groups, name='group'),
    path('group/<int:pk>/', group_views.group_detail, name='group_detail'),
    path('group/<int:pk>/invite/', group_views.group_invite, name='group_invite'),
    path('group/<int:pk>/leave/', group_views.group_leave, name='group_leave'),
    path('group/<int:pk>/member/<int:mpk>/remove/', group_views.member_remove, name='member_remove'),
    path('group/<int:pk>/research/new/', group_views.research_new, name='research_new'),
    path('group/invite/<int:mpk>/accept/', group_views.invite_accept, name='invite_accept'),
    path('group/invite/<int:mpk>/decline/', group_views.invite_decline, name='invite_decline'),
    path('assistant/', views.assistant, name='assistant'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('profile/', profile_views.profile, name='profile'),
    path('search/', views.search, name='search'),
]
