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
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


# Create your views here.


def home(request):
    total_users = User.objects.count()
    return render(request, 'management/home.html', {
        'total_users' : total_users
    })


def anSentimientos(request):
    return render(request, 'management/ansentimientos.html')

def analytics(request):
    return render(request, 'management/analytics.html')

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
                  return redirect('home')
             else:
                  return redirect('user_home')
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
##Vista Admon
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_users_crud(request):    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            return create_user(request)
        elif action == 'update':
            return update_user(request)
        elif action == 'delete':
            return delete_user(request)
    
    # GET 
    users = User.objects.all().select_related().order_by('username')
    total_users = users.count()

    context = {
        'users': users,
        'total_users': users.count(),
        'total_users': total_users, 
        'active_users': users.filter(is_active=True).count(),
    }
    
    return render(request, 'management/users_crud.html', context)

def create_user(request):
    try:
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario {username} ya existe')
            return redirect('management/users_crud.html')
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
            is_active=is_active
        )
        
        messages.success(request, f'Usuario {username} creado exitosamente')
        
    except Exception as e:
        messages.error(request, f'Error al crear usuario: {str(e)}')
    return redirect('admin_crud')

def update_user(request):
    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        # Actualizar campos
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_active = request.POST.get('is_active') == 'on'
        
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        messages.success(request, f'Usuario {user.username} actualizado exitosamente')
        
    except Exception as e:
        messages.error(request, f'Error al actualizar él usuario: {str(e)}')
    
    return redirect('admin_crud')

def delete_user(request):
    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        username = user.username
        
        # No permitir que el admin se elimine a sí mismo
        if user == request.user:
            messages.error(request, 'No puedes eliminarte a ti mismo porque eres admin')
            return redirect('admin_crud')
        
        user.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente')
        
    except Exception as e:
        messages.error(request, f'Error al eliminar l usuario: {str(e)}')
    
    return redirect('admin_crud')

@login_required
@user_passes_test(is_admin)
def get_user_data(request, user_id):
    """API para obtener datos del usuario para edición (AJAX)"""
    try:
        user = get_object_or_404(User, id=user_id)
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Nunca'
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    







    ## USER LOGIC
def user_home(request):
    return render (request, 'Users/home_user.html')

def chat(request):
    return render (request, 'Users/chat.html')

def contactos(request):
    return render (request, 'Users/contacts.html')

def perfil(request):
    return render (request, 'Users/perfil.html')