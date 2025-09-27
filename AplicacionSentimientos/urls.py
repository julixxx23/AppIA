# AplicacionSentimientos/urls.py

from django.contrib import admin
from django.urls import path
from AppIA import views

urlpatterns = [
    # URLs de Administración y Autenticación
    path('admin/', admin.site.urls),
    path('', views.signin, name='login'),
    path('signup/', views.signup, name='signup'),
    path('home/', views.home, name='home'),
    
    # URLs del Chat
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/conversation/<int:conversation_id>/', views.chat_detail, name='chat_detail'),
    path('chat/start/', views.start_conversation, name='start_conversation'),
    path('chat/send-message/', views.send_message, name='send_message'),
    path('chat/get-messages/<int:conversation_id>/', views.get_messages, name='get_messages'),
    path('chat/search-users/', views.search_users, name='search_users'),


    

    # URLs del dashboard de análisis - AGREGAR ESTAS LÍNEAS:
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/conversation/<int:conversation_id>/analyze/', views.generate_conversation_analysis, name='generate_conversation_analysis'),
    path('admin-dashboard/report/<int:report_id>/', views.conversation_analysis_report, name='conversation_analysis_report'),
    path('admin-dashboard/general-analysis/', views.generate_general_analysis, name='generate_general_analysis'),
]