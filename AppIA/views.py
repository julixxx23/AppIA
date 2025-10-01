# --- Imports de Django ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q, Max
from django.http import JsonResponse
from django.contrib import messages
from django import forms
import json

# --- Imports de la Aplicación ---
from .models import Conversation, Message, MessageAnalysis, ConversationAnalysisReport
from .ml import predict_emotion


# --- Vistas Generales y de Autenticación ---
from .analytics_utils import (
    generate_distribution_chart,
    generate_bar_chart,
    generate_temporal_chart,
    generate_user_chart
)

def home(request):
    total_users = User.objects.count()
    return render(request, 'management/home.html', {
        'total_users': total_users
    })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def anSentimientos(request):
    """Dashboard de análisis de sentimientos en management"""
    conversations = Conversation.objects.all()
    recent_reports = ConversationAnalysisReport.objects.order_by('-created_at')[:5]
    
    context = {
        'conversations': conversations,
        'total_conversations': conversations.count(),
        'total_messages': Message.objects.count(),
        'recent_reports': recent_reports,
    }
    return render(request, 'management/ansentimientos.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def analytics(request):
    """Dashboard de analytics con gráficos comparativos"""
    
    # Obtener todos los análisis
    all_analyses = MessageAnalysis.objects.all()
    total_analyses = all_analyses.count()
    
    if total_analyses == 0:
        context = {
            'total_analyses': 0,
            'neutral_count': 0,
            'positive_count': 0,
            'harassment_count': 0,
            'extortion_count': 0,
            'neutral_percentage': 0,
            'positive_percentage': 0,
            'harassment_percentage': 0,
            'extortion_percentage': 0,
            'positive_trend': True,
            'trend_change': 0,
            'period_data': []
        }
        return render(request, 'management/analytics.html', context)
    
    # Contar por categorías
    neutral_count = all_analyses.filter(emotion_label='Neutral').count()
    positive_count = all_analyses.filter(emotion_label='Positivo').count()
    harassment_count = all_analyses.filter(emotion_label='Acoso/Violencia').count()
    extortion_count = all_analyses.filter(emotion_label='Extorsión').count()
    
    # Calcular porcentajes
    neutral_percentage = (neutral_count / total_analyses) * 100
    positive_percentage = (positive_count / total_analyses) * 100
    harassment_percentage = (harassment_count / total_analyses) * 100
    extortion_percentage = (extortion_count / total_analyses) * 100
    
    # Datos por período (últimos 7 días)
    today = datetime.now().date()
    period_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_analyses = all_analyses.filter(analyzed_at__date=date)
        
        period_data.append({
            'name': date.strftime('%d/%m'),
            'total': day_analyses.count(),
            'neutral': day_analyses.filter(emotion_label='Neutral').count(),
            'positive': day_analyses.filter(emotion_label='Positivo').count(),
            'harassment': day_analyses.filter(emotion_label='Acoso/Violencia').count(),
            'extortion': day_analyses.filter(emotion_label='Extorsión').count(),
        })
    
    context = {
        'total_analyses': total_analyses,
        'neutral_count': neutral_count,
        'positive_count': positive_count,
        'harassment_count': harassment_count,
        'extortion_count': extortion_count,
        'neutral_percentage': neutral_percentage,
        'positive_percentage': positive_percentage,
        'harassment_percentage': harassment_percentage,
        'extortion_percentage': extortion_percentage,
        'positive_trend': True,
        'trend_change': 5.2,
        'period_data': period_data
    }
    
    return render(request, 'management/analytics.html', context)

def signup(request):
    if request.method == 'GET':
        return render(request, 'registro.html', {
            'form': UserCreationForm
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                    username=request.POST['username'],
                    password=request.POST['password2']
                )
                user.save()
                login(request, user)
                return redirect('home')
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

# --- Lógica de Usuario ---
def user_home(request):
    return render(request, 'Users/home_user.html')


# --- Funciones y Formularios de Administración ---

def is_admin(user):
    return user.is_superuser or user.is_staff

class AdminUser(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="El usuario usará esta contraseña para iniciar sesión"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        labels = {
            'username': 'Nombre usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'password': 'Contraseña'
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class update(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_active': 'Usuario activo'
        }

# --- Vistas de Administración de Usuarios (CRUD) ---

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
    users = User.objects.all().order_by('username')
    context = {
        'users': users,
        'total_users': users.count(),
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
            return redirect('admin_crud')

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
            is_staff=is_staff, is_active=is_active
        )
        messages.success(request, f'Usuario {username} creado exitosamente')

    except Exception as e:
        messages.error(request, f'Error al crear usuario: {str(e)}')
    return redirect('admin_crud')

def update_user(request):
    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)

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
        messages.error(request, f'Error al actualizar el usuario: {str(e)}')
    return redirect('admin_crud')

def delete_user(request):
    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        username = user.username

        if user == request.user:
            messages.error(request, 'No puedes eliminarte a ti mismo.')
            return redirect('admin_crud')

        user.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente')

    except Exception as e:
        messages.error(request, f'Error al eliminar el usuario: {str(e)}')
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


# --- Vistas del Chat ---

@login_required
def chat_list(request):
    conversations = request.user.conversations.annotate(
        last_message_time=Max('messages__created_at')
    ).order_by('-last_message_time')
    
    users = User.objects.exclude(id=request.user.id).filter(is_active=True)
    
    context = {
        'conversations': conversations,
        'users': users
    }
    return render(request, 'chat/chat_list.html', context)

@login_required
def start_conversation(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            other_user = User.objects.get(id=user_id)
            
            existing_conversation = Conversation.objects.filter(
                participants=request.user
            ).filter(participants=other_user).first()
            
            if existing_conversation:
                return redirect('chat_detail', conversation_id=existing_conversation.id)
            
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            
            return redirect('chat_detail', conversation_id=conversation.id)
            
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return redirect('chat_list')
    return redirect('chat_list')

@login_required
def chat_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.user not in conversation.participants.all():
        messages.error(request, 'No tienes acceso a esta conversación')
        return redirect('chat_list')
    
    chat_messages = conversation.messages.order_by('created_at')
    other_participant = conversation.get_other_participant(request.user)
    
    context = {
        'conversation': conversation,
        'messages': chat_messages,
        'other_participant': other_participant,
    }
    return render(request, 'chat/chat_detail.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            content = data.get('content', '').strip()
            
            if not content:
                return JsonResponse({'error': 'El mensaje no puede estar vacío'}, status=400)
            
            conversation = get_object_or_404(Conversation, id=conversation_id)
            
            if request.user not in conversation.participants.all():
                return JsonResponse({'error': 'No autorizado'}, status=403)
            
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
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
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.user not in conversation.participants.all():
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    last_message_id = request.GET.get('last_message_id', 0)
    
    new_messages = conversation.messages.filter(id__gt=last_message_id).order_by('created_at')
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'sender': msg.sender.username,
        'created_at': msg.created_at.strftime('%H:%M'),
        'is_own': msg.sender == request.user
    } for msg in new_messages]
    
    return JsonResponse({'messages': messages_data})

@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id).filter(is_active=True)[:10]
    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'full_name': f"{user.first_name} {user.last_name}".strip() or user.username
    } for user in users]
    
    return JsonResponse({'users': users_data})


# --- Vistas del Dashboard de Análisis de Sentimientos ---

@user_passes_test(is_admin)
def admin_dashboard(request):
    conversations = Conversation.objects.all()
    recent_reports = ConversationAnalysisReport.objects.order_by('-created_at')[:5]
    
    context = {
        'conversations': conversations,
        'total_conversations': conversations.count(),
        'total_messages': Message.objects.count(),
        'recent_reports': recent_reports,
    }
    return render(request, 'admin/dashboard.html', context)

@user_passes_test(is_admin)
def generate_conversation_analysis(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    
    if request.method == 'POST':
        messages_to_analyze = conversation.messages.all()
        analysis_data = {
            'total_messages': 0, 'neutral_count': 0, 'positive_count': 0,
            'harassment_count': 0, 'extortion_count': 0
        }
        
        for message in messages_to_analyze:
            try:
                result = predict_emotion(message.content)
                
                message_analysis, created = MessageAnalysis.objects.update_or_create(
                    message=message,
                    defaults={
                        'emotion_label': result['etiqueta'],
                        'confidence': result['confianza']
                    }
                )
                
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
        
        total = analysis_data['total_messages']
        if total > 0:
            analysis_data['neutral_percentage'] = (analysis_data['neutral_count'] / total) * 100
            analysis_data['positive_percentage'] = (analysis_data['positive_count'] / total) * 100
            analysis_data['harassment_percentage'] = (analysis_data['harassment_count'] / total) * 100
            analysis_data['extortion_percentage'] = (analysis_data['extortion_count'] / total) * 100
        
        report = ConversationAnalysisReport.objects.create(
            conversation=conversation,
            created_by=request.user,
            **analysis_data
        )
        
        messages.success(request, f'Análisis completado. Se analizaron {total} mensajes.')
        return redirect('conversation_analysis_report', report_id=report.id)
    
    context = {
        'conversation': conversation,
        'participants': conversation.participants.all(),
        'message_count': conversation.messages.count(),
    }
    return render(request, 'management/generate_analysis.html', context)

@user_passes_test(is_admin)
def conversation_analysis_report(request, report_id):
    report = get_object_or_404(ConversationAnalysisReport, id=report_id)
    analyzed_messages = Message.objects.filter(
        conversation=report.conversation,
        analysis__isnull=False
    ).select_related('analysis', 'sender')
    
    problematic_messages = analyzed_messages.filter(
        analysis__emotion_label__in=['Acoso/Violencia', 'Extorsión']
    )
    
    context = {
        'report': report,
        'conversation': report.conversation,
        'analyzed_messages': analyzed_messages,
        'problematic_messages': problematic_messages,
    }
    return render(request, 'management/conversation_report.html', context)

@user_passes_test(is_admin)
def generate_general_analysis(request):
    if request.method == 'POST':
        all_messages = Message.objects.all()
        analysis_data = {
            'total_messages': 0, 'neutral_count': 0, 'positive_count': 0,
            'harassment_count': 0, 'extortion_count': 0
        }
        
        processed_count = 0
        for message in all_messages:
            try:
                result = predict_emotion(message.content)
                MessageAnalysis.objects.update_or_create(
                    message=message,
                    defaults={
                        'emotion_label': result['etiqueta'],
                        'confidence': result['confianza']
                    }
                )
                
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
        
        total = analysis_data['total_messages']
        if total > 0:
            analysis_data['neutral_percentage'] = (analysis_data['neutral_count'] / total) * 100
            analysis_data['positive_percentage'] = (analysis_data['positive_count'] / total) * 100
            analysis_data['harassment_percentage'] = (analysis_data['harassment_count'] / total) * 100
            analysis_data['extortion_percentage'] = (analysis_data['extortion_count'] / total) * 100
        
        messages.success(request, f'Análisis general completado. Se procesaron {processed_count} mensajes.')
        
        return render(request, 'management/general_report.html', {
            'analysis_data': analysis_data,
            'processed_count': processed_count
        })
    
    context = {
        'total_messages': Message.objects.count(),
        'total_conversations': Conversation.objects.count(),
    }
    return render(request, 'management/generate_general_analysis.html', context)