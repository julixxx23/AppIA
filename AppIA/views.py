from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login
from django.db import IntegrityError
from django.contrib import messages
from django.forms import ModelForm
from django.db.models import Q, Max
import json
from django import forms
from .models import Conversation, Message

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


# FUNCIONES DEL CHAT  

@login_required
def chat_list(request):
    """Vista principal del chat - lista de conversaciones"""
    conversations = request.user.conversations.annotate(
        last_message_time=Max('messages__created_at')
    ).order_by('-last_message_time')
    
    # Obtener usuarios disponibles para iniciar nueva conversación
    users = User.objects.exclude(id=request.user.id).filter(is_active=True)
    
    context = {
        'conversations': conversations,
        'users': users
    }
    return render(request, 'chat/chat_list.html', context)

@login_required
def start_conversation(request):
    """Iniciar una nueva conversación"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            other_user = User.objects.get(id=user_id)
            
            # Verificar si ya existe una conversación entre estos usuarios
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(participants=other_user).first()
            
            if existing_conversation:
                return redirect('chat_detail', conversation_id=existing_conversation.id)
            
            # Crear nueva conversación
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            
            return redirect('chat_detail', conversation_id=conversation.id)
            
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return redirect('chat_list')
    
    return redirect('chat_list')

@login_required
def chat_detail(request, conversation_id):
    """Vista detallada de una conversación específica"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    # Verificar que el usuario es participante de la conversación
    if request.user not in conversation.participants.all():
        messages.error(request, 'No tienes acceso a esta conversación')
        return redirect('chat_list')
    
    # Obtener mensajes de la conversación
    chat_messages = conversation.messages.order_by('created_at')
    
    # Obtener el otro participante
    other_participant = conversation.get_other_participant(request.user)
    
    context = {
        'conversation': conversation,
        'messages': chat_messages,
        'other_participant': other_participant,
    }
    return render(request, 'chat/chat_detail.html', context)

@login_required
def send_message(request):
    """Enviar un mensaje vía AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            content = data.get('content', '').strip()
            
            if not content:
                return JsonResponse({'error': 'El mensaje no puede estar vacío'}, status=400)
            
            conversation = get_object_or_404(Conversation, id=conversation_id)
            
            # Verificar que el usuario es participante
            if request.user not in conversation.participants.all():
                return JsonResponse({'error': 'No autorizado'}, status=403)
            
            # Crear el mensaje
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Actualizar timestamp de la conversación
            conversation.save()
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'content': message.content,
                'sender': message.sender.username,
                'created_at': message.created_at.strftime('%H:%M'),
                'is_own': True
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos inválidos'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def get_messages(request, conversation_id):
    """Obtener mensajes nuevos vía AJAX"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.user not in conversation.participants.all():
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    last_message_id = request.GET.get('last_message_id', 0)
    
    new_messages = conversation.messages.filter(
        id__gt=last_message_id
    ).order_by('created_at')
    
    messages_data = []
    for message in new_messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'sender': message.sender.username,
            'created_at': message.created_at.strftime('%H:%M'),
            'is_own': message.sender == request.user
        })
    
    return JsonResponse({'messages': messages_data})

@login_required
def search_users(request):
    """Buscar usuarios para iniciar conversación"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).filter(is_active=True)[:10]
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username
        })
    
    return JsonResponse({'users': users_data})


# AGREGAR AL FINAL DE AppIA/views.py (después de las funciones del chat)

from .models import MessageAnalysis, ConversationAnalysisReport
from .ml import predict_emotion

# Dashboard de administración principal
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Vista principal del dashboard de administración"""
    conversations = Conversation.objects.all()
    total_conversations = conversations.count()
    total_messages = Message.objects.count()
    
    # Reportes recientes
    recent_reports = ConversationAnalysisReport.objects.all()[:5]
    
    context = {
        'conversations': conversations,
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'recent_reports': recent_reports,
    }
    return render(request, 'admin/dashboard.html', context)

# Generar análisis de una conversación específica
@user_passes_test(is_admin)
def generate_conversation_analysis(request, conversation_id):
    """Genera análisis de una conversación específica"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    messages = conversation.messages.all()
    
    if request.method == 'POST':
        # Procesar mensajes con la red neuronal
        analysis_data = {
            'total_messages': 0,
            'neutral_count': 0,
            'positive_count': 0,
            'harassment_count': 0,
            'extortion_count': 0,
        }
        
        # Analizar cada mensaje
        for message in messages:
            try:
                # Usar tu red neuronal para analizar
                result = predict_emotion(message.content)
                
                # Crear o actualizar análisis del mensaje
                message_analysis, created = MessageAnalysis.objects.get_or_create(
                    message=message,
                    defaults={
                        'emotion_label': result['etiqueta'],
                        'confidence': result['confianza']
                    }
                )
                
                # Si ya existía, actualizar
                if not created:
                    message_analysis.emotion_label = result['etiqueta']
                    message_analysis.confidence = result['confianza']
                    message_analysis.save()
                
                # Contar por categorías
                analysis_data['total_messages'] += 1
                if result['etiqueta'] == 'Neutral':
                    analysis_data['neutral_count'] += 1
                elif result['etiqueta'] == 'Positivo':
                    analysis_data['positive_count'] += 1
                elif result['etiqueta'] == 'Acoso/Violencia':
                    analysis_data['harassment_count'] += 1
                elif result['etiqueta'] == 'Extorsión':
                    analysis_data['extortion_count'] += 1
                    
            except Exception as e:
                print(f"Error analizando mensaje {message.id}: {e}")
        
        # Calcular porcentajes
        total = analysis_data['total_messages']
        if total > 0:
            analysis_data['neutral_percentage'] = (analysis_data['neutral_count'] / total) * 100
            analysis_data['positive_percentage'] = (analysis_data['positive_count'] / total) * 100
            analysis_data['harassment_percentage'] = (analysis_data['harassment_count'] / total) * 100
            analysis_data['extortion_percentage'] = (analysis_data['extortion_count'] / total) * 100
        
        # Crear reporte
        report = ConversationAnalysisReport.objects.create(
            conversation=conversation,
            created_by=request.user,
            **analysis_data
        )
        
        messages.success(request, f'Análisis completado. Se analizaron {total} mensajes.')
        return redirect('conversation_analysis_report', report_id=report.id)
    
    # GET request - mostrar formulario de confirmación
    participants = conversation.participants.all()
    context = {
        'conversation': conversation,
        'participants': participants,
        'message_count': messages.count(),
    }
    return render(request, 'admin/generate_analysis.html', context)

# Ver reporte de análisis de conversación
@user_passes_test(is_admin)
def conversation_analysis_report(request, report_id):
    """Muestra el reporte de análisis de una conversación"""
    report = get_object_or_404(ConversationAnalysisReport, id=report_id)
    conversation = report.conversation
    
    # Obtener mensajes analizados
    analyzed_messages = Message.objects.filter(
        conversation=conversation,
        analysis__isnull=False
    ).select_related('analysis', 'sender')
    
    # Mensajes problemáticos (acoso + extorsión)
    problematic_messages = analyzed_messages.filter(
        analysis__emotion_label__in=['Acoso/Violencia', 'Extorsión']
    )
    
    context = {
        'report': report,
        'conversation': conversation,
        'analyzed_messages': analyzed_messages,
        'problematic_messages': problematic_messages,
    }
    return render(request, 'admin/conversation_report.html', context)

# Dashboard general de todas las conversaciones
@user_passes_test(is_admin)
def generate_general_analysis(request):
    """Genera análisis general de todas las conversaciones"""
    if request.method == 'POST':
        # Obtener todos los mensajes
        all_messages = Message.objects.all()
        
        analysis_data = {
            'total_messages': 0,
            'neutral_count': 0,
            'positive_count': 0,
            'harassment_count': 0,
            'extortion_count': 0,
        }
        
        # Procesar cada mensaje
        processed_count = 0
        for message in all_messages:
            try:
                result = predict_emotion(message.content)
                
                # Crear o actualizar análisis
                message_analysis, created = MessageAnalysis.objects.get_or_create(
                    message=message,
                    defaults={
                        'emotion_label': result['etiqueta'],
                        'confidence': result['confianza']
                    }
                )
                
                if not created:
                    message_analysis.emotion_label = result['etiqueta']
                    message_analysis.confidence = result['confianza']
                    message_analysis.save()
                
                # Contar categorías
                analysis_data['total_messages'] += 1
                if result['etiqueta'] == 'Neutral':
                    analysis_data['neutral_count'] += 1
                elif result['etiqueta'] == 'Positivo':
                    analysis_data['positive_count'] += 1
                elif result['etiqueta'] == 'Acoso/Violencia':
                    analysis_data['harassment_count'] += 1
                elif result['etiqueta'] == 'Extorsión':
                    analysis_data['extortion_count'] += 1
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error analizando mensaje {message.id}: {e}")
        
        # Calcular porcentajes
        total = analysis_data['total_messages']
        if total > 0:
            analysis_data['neutral_percentage'] = (analysis_data['neutral_count'] / total) * 100
            analysis_data['positive_percentage'] = (analysis_data['positive_count'] / total) * 100
            analysis_data['harassment_percentage'] = (analysis_data['harassment_count'] / total) * 100
            analysis_data['extortion_percentage'] = (analysis_data['extortion_count'] / total) * 100
        
        messages.success(request, f'Análisis general completado. Se procesaron {processed_count} mensajes.')
        
        return render(request, 'admin/general_report.html', {
            'analysis_data': analysis_data,
            'processed_count': processed_count
        })
    
    # GET request
    total_messages = Message.objects.count()
    total_conversations = Conversation.objects.count()
    
    context = {
        'total_messages': total_messages,
        'total_conversations': total_conversations,
    }
    return render(request, 'admin/generate_general_analysis.html', context)