from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib.auth import login
from django.db import IntegrityError
from django.contrib import messages
from django.forms import ModelForm
from django import forms

# Create your views here.


def home(request):
    return render(request, 'home.html')

# Registrar
def signup(request):

    if request.method == 'GET':
        return render(request, 'registro.html', {
            'form': UserCreationForm
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            # registrar usuario
            try:
                user = User.objects.create_user(username=request.POST['username'],
                                                password=request.POST['password2'])
                user.save()
                login(request, user)
                return redirect ('home')
            except IntegrityError:
                return render(request, 'registro.html', {
                    'form': UserCreationForm,
                    "error": 'El usuario ya existe'
                })
        return render(request, 'registro.html', {
            'form': UserCreationForm,
            "error": 'Las contraseñas no coinciden'
        })
    
def signin(request):
     if request.method == 'GET':
          return render(request, 'login.html')
     else:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
             login(request, user)
             if user.is_superuser or user.is_staff:
                  return redirect('admin_dashboard')
             else:
                  return redirect('home')
        else:
             return render(request, 'login.html', {
                  'error': 'Usuario o contraseña incorrectos'
             })

# Usuario Admin
def is_admin(user):
    return user.is_superuser or user.is_staff

class AdminUser(forms.ModelForm):
        password = forms.CharField(
            widget=forms.PasswordInput,
            help_text="El usuario usaá esta contraseña para inciar sesión"
        )

        class Meta: 
            model = User
            fields = ['username', 'email', 'first_name', 'last_name', 'password']
            labels = {
                'username' : 'Nombre usuario',
                'email' : 'correo electronico',
                'first_name' : 'Nombre',
                'last_name' : 'Apellido',
                'password' : 'contraseña'
            }
        def save(self, commit=True): 
            user = super().save(commit=False)
            user.set_password(self.cleaned_data['password'])
            if commit: 
                user.save()
            return user
class update(forms.ModelForm):
    class Meta : 
            model = User
            fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
            labels = {
                'username': 'Nombre de usuario',
                'email': 'Correo electrónico', 
                'first_name': 'Nombre',
                'last_name': 'Apellido',
                'is_active': 'Usuario activo'
            }
##@login_required
##@user_passes_test(is_admin)
##def adminView(request)
  ##  """Panel principal del administrador"""
  ##  total_users = User.objects.count()
  ##  active_users = User.objects.filter