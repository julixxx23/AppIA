"""
URL configuration for AplicacionSentimientos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from AppIA import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.signin, name='login'),
    path('signup/', views.signup, name='signup'),
    path('home/', views.home, name='home'),
    path('management/users/', views.admin_users_crud, name='admin_crud' ),
    path('management/users/<int:user_id>/data/', views.get_user_data, name='get_user_data'),
    path('anSentimientos/', views.anSentimientos, name='anSentimientos' ),
    path('analytics/', views.analytics, name='analytics'),

    ## USER
    path('user_home/', views.user_home, name='user_home'),
    path('user_chat', views.chat, name='chat'),
    path('user_contactos', views.contactos, name='contactos'),
    path('user_perfil', views.perfil, name='perfil'),
]
