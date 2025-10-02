# --- Imports de Django ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q, Max, Count
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django import forms
import json
from datetime import datetime, timedelta

# --- Imports de ReportLab para PDF ---
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO

# --- Imports de la Aplicación ---
from .models import Conversation, Message, MessageAnalysis, ConversationAnalysisReport
from .ml import predict_emotion
from .analytics_utils import (
    generate_distribution_chart,
    generate_bar_chart,
    generate_temporal_chart,
    generate_user_chart
)


# --- Vistas Generales y de Autenticación ---

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
    """Dashboard de analytics con gráficos generados por Matplotlib"""
    
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
            'period_data': [],
            'distribution_chart': None,
            'bar_chart': None,
            'temporal_chart': None,
            'user_chart': None
        }
        return render(request, 'management/analytics.html', context)
    
    # Contar por categorías
    neutral_count = all_analyses.filter(emotion_label='Neutral').count()
    positive_count = all_analyses.filter(emotion_label='Positivo').count()
    harassment_count = all_analyses.filter(emotion_label='Acoso/Violencia').count()
    extortion_count = all_analyses.filter(emotion_label='Extorsión').count()
    
    # Calcular porcentajes
    analysis_data = {
        'neutral_count': neutral_count,
        'positive_count': positive_count,
        'harassment_count': harassment_count,
        'extortion_count': extortion_count,
        'neutral_percentage': (neutral_count / total_analyses) * 100,
        'positive_percentage': (positive_count / total_analyses) * 100,
        'harassment_percentage': (harassment_count / total_analyses) * 100,
        'extortion_percentage': (extortion_count / total_analyses) * 100
    }
    
    # Top 5 usuarios más activos
    top_users = Message.objects.values('sender__username').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    top_users_data = [{'username': user['sender__username'], 'count': user['count']} 
                      for user in top_users]
    
    # Generar gráficas con Matplotlib
    distribution_chart = generate_distribution_chart(analysis_data)
    bar_chart = generate_bar_chart(analysis_data)
    temporal_chart = generate_temporal_chart(all_analyses)
    user_chart = generate_user_chart(top_users_data) if top_users_data else None
    
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
        'neutral_percentage': analysis_data['neutral_percentage'],
        'positive_percentage': analysis_data['positive_percentage'],
        'harassment_percentage': analysis_data['harassment_percentage'],
        'extortion_percentage': analysis_data['extortion_percentage'],
        'positive_trend': True,
        'trend_change': 5.2,
        'period_data': period_data,
        'distribution_chart': distribution_chart,
        'bar_chart': bar_chart,
        'temporal_chart': temporal_chart,
        'user_chart': user_chart
    }
    
    return render(request, 'management/analytics.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def export_analytics_pdf(request):
    """Exportar reporte de analytics en formato PDF"""
    
    # Crear el objeto HttpResponse con el tipo MIME apropiado para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="analytics_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    # Crear el buffer
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Obtener datos (mismo código que en la vista analytics)
    all_analyses = MessageAnalysis.objects.all()
    total_analyses = all_analyses.count()
    
    # Título del reporte
    title = Paragraph("Reporte de Analytics - Análisis de Sentimientos", title_style)
    elements.append(title)
    
    # Fecha de generación
    date_text = Paragraph(
        f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        styles['Normal']
    )
    elements.append(date_text)
    elements.append(Spacer(1, 20))
    
    if total_analyses == 0:
        no_data = Paragraph("No hay datos de análisis disponibles.", styles['Normal'])
        elements.append(no_data)
    else:
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
        
        # Resumen general
        elements.append(Paragraph("Resumen General", heading_style))
        
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de análisis', str(total_analyses)],
            ['Mensajes neutrales', f"{neutral_count} ({neutral_percentage:.1f}%)"],
            ['Mensajes positivos', f"{positive_count} ({positive_percentage:.1f}%)"],
            ['Mensajes de acoso/violencia', f"{harassment_count} ({harassment_percentage:.1f}%)"],
            ['Mensajes de extorsión', f"{extortion_count} ({extortion_percentage:.1f}%)"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 30))
        
        # Distribución por categoría
        elements.append(Paragraph("Distribución por Categoría", heading_style))
        
        category_data = [
            ['Categoría', 'Cantidad', 'Porcentaje'],
            ['Neutral', str(neutral_count), f"{neutral_percentage:.2f}%"],
            ['Positivo', str(positive_count), f"{positive_percentage:.2f}%"],
            ['Acoso/Violencia', str(harassment_count), f"{harassment_percentage:.2f}%"],
            ['Extorsión', str(extortion_count), f"{extortion_percentage:.2f}%"],
        ]
        
        category_table = Table(category_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        
        elements.append(category_table)
        elements.append(Spacer(1, 30))
        
        # Top 5 usuarios más activos
        top_users = Message.objects.values('sender__username').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        if top_users:
            elements.append(Paragraph("Top 5 Usuarios Más Activos", heading_style))
            
            users_data = [['Usuario', 'Mensajes']]
            for user in top_users:
                users_data.append([user['sender__username'], str(user['count'])])
            
            users_table = Table(users_data, colWidths=[3*inch, 2*inch])
            users_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            elements.append(users_table)
            elements.append(Spacer(1, 30))
        
        # Análisis temporal (últimos 7 días)
        elements.append(Paragraph("Análisis Temporal (Últimos 7 Días)", heading_style))
        
        today = datetime.now().date()
        temporal_data = [['Fecha', 'Total', 'Neutral', 'Positivo', 'Acoso', 'Extorsión']]
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            day_analyses = all_analyses.filter(analyzed_at__date=date)
            temporal_data.append([
                date.strftime('%d/%m/%Y'),
                str(day_analyses.count()),
                str(day_analyses.filter(emotion_label='Neutral').count()),
                str(day_analyses.filter(emotion_label='Positivo').count()),
                str(day_analyses.filter(emotion_label='Acoso/Violencia').count()),
                str(day_analyses.filter(emotion_label='Extorsión').count()),
            ])
        
        temporal_table = Table(temporal_data, colWidths=[1.3*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.9*inch])
        temporal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        
        elements.append(temporal_table)
        
        # Pie de página
        elements.append(Spacer(1, 50))
        footer = Paragraph(
            "<i>Este reporte fue generado automáticamente por el Sistema de Análisis de Sentimientos</i>",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        )
        elements.append(footer)
    
    # Construir el PDF
    doc.build(elements)
    
    # Obtener el valor del buffer y escribirlo en la respuesta
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

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
@login_required
def user_home(request):
    """Vista del home del usuario con estadísticas personales"""

    # Obtener conversaciones del usuario
    user_conversations = request.user.conversations.count()

    # Obtener contactos (usuarios activos excepto el usuario actual y admins)
    total_contacts = User.objects.exclude(id=request.user.id).filter(
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()

    # Calcular estado de ánimo basado en análisis de sentimientos
    user_analyses = MessageAnalysis.objects.filter(
        message__sender=request.user
    )

    total_analyses = user_analyses.count()
    mood_score = 50  # Default: neutral

    if total_analyses > 0:
        # Calcular porcentajes
        positive_count = user_analyses.filter(emotion_label='Positivo').count()
        neutral_count = user_analyses.filter(emotion_label='Neutral').count()
        harassment_count = user_analyses.filter(emotion_label='Acoso/Violencia').count()
        extortion_count = user_analyses.filter(emotion_label='Extorsión').count()

        # Calcular score ponderado (0-100)
        # Positivo: +100, Neutral: +50, Negativos: 0
        total_score = (positive_count * 100) + (neutral_count * 50) + (harassment_count * 0) + (extortion_count * 0)
        mood_score = int(total_score / total_analyses) if total_analyses > 0 else 50

    context = {
        'total_conversations': user_conversations,
        'total_contacts': total_contacts,
        'mood_score': mood_score,
    }

    return render(request, 'Users/home_user.html', context)

@login_required
def contactos(request):
    """Vista de contactos del usuario"""
    # Obtener todos los usuarios excepto el usuario actual
    all_users = User.objects.exclude(id=request.user.id).filter(is_active=True)

    # Obtener usuarios con los que ya tiene conversaciones
    conversations = request.user.conversations.all()
    users_with_conversations = set()
    for conversation in conversations:
        other_user = conversation.get_other_participant(request.user)
        if other_user:
            users_with_conversations.add(other_user.id)

    context = {
        'all_users': all_users,
        'users_with_conversations': users_with_conversations,
        'total_contacts': all_users.count()
    }
    return render(request, 'Users/contacts.html', context)

@login_required
def perfil(request):
    """Vista del perfil del usuario con edición"""

    if request.method == 'POST':
        # Actualizar información personal
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')

        # Cambiar contraseña si se proporciona
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if current_password and new_password:
            # Verificar contraseña actual
            if not request.user.check_password(current_password):
                messages.error(request, 'La contraseña actual es incorrecta')
            elif new_password != confirm_password:
                messages.error(request, 'Las contraseñas nuevas no coinciden')
            elif len(new_password) < 6:
                messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
            else:
                request.user.set_password(new_password)
                request.user.save()
                # Re-autenticar al usuario
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Perfil y contraseña actualizados exitosamente')
                return redirect('perfil')

        request.user.save()
        messages.success(request, 'Perfil actualizado exitosamente')
        return redirect('perfil')

    # Estadísticas del usuario
    user_conversations = request.user.conversations.count()
    user_messages = request.user.sent_messages.count()

    # Obtener análisis de mensajes del usuario
    user_analyses = MessageAnalysis.objects.filter(
        message__sender=request.user
    )

    # Calcular distribución emocional
    total_analyses = user_analyses.count()
    emotion_stats = {
        'neutral': 0,
        'positive': 0,
        'harassment': 0,
        'extortion': 0
    }

    if total_analyses > 0:
        neutral_count = user_analyses.filter(emotion_label='Neutral').count()
        positive_count = user_analyses.filter(emotion_label='Positivo').count()
        harassment_count = user_analyses.filter(emotion_label='Acoso/Violencia').count()
        extortion_count = user_analyses.filter(emotion_label='Extorsión').count()

        emotion_stats['neutral'] = int((neutral_count / total_analyses) * 100)
        emotion_stats['positive'] = int((positive_count / total_analyses) * 100)
        emotion_stats['harassment'] = int((harassment_count / total_analyses) * 100)
        emotion_stats['extortion'] = int((extortion_count / total_analyses) * 100)

    context = {
        'user_conversations': user_conversations,
        'user_messages': user_messages,
        'total_analyses': total_analyses,
        'emotion_stats': emotion_stats
    }
    return render(request, 'Users/perfil.html', context)


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

    # Agregar el otro participante a cada conversación
    conversations_with_other = []
    for conversation in conversations:
        conversation.other_participant = conversation.get_other_participant(request.user)
        conversations_with_other.append(conversation)

    users = User.objects.exclude(id=request.user.id).filter(is_active=True)

    context = {
        'conversations': conversations_with_other,
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
def export_conversation_pdf(request, report_id):
    """Exportar reporte de conversación específica en formato PDF"""

    report = get_object_or_404(ConversationAnalysisReport, id=report_id)
    conversation = report.conversation

    # Crear el objeto HttpResponse con el tipo MIME apropiado para PDF
    participants_names = "_".join([p.username for p in conversation.participants.all()])
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="conversation_{participants_names}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'

    # Crear el buffer
    buffer = BytesIO()

    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Contenedor para los elementos del PDF
    elements = []

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=12
    )

    # Título del reporte
    title = Paragraph(f"Reporte de Análisis de Conversación", title_style)
    elements.append(title)

    # Participantes
    participants = ", ".join([user.username for user in conversation.participants.all()])
    participants_text = Paragraph(
        f"<b>Participantes:</b> {participants}",
        styles['Normal']
    )
    elements.append(participants_text)

    # Fecha de generación
    date_text = Paragraph(
        f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        styles['Normal']
    )
    elements.append(date_text)

    # Generado por
    created_by_text = Paragraph(
        f"<b>Generado por:</b> {report.created_by.username}",
        styles['Normal']
    )
    elements.append(created_by_text)
    elements.append(Spacer(1, 20))

    # Resumen general
    elements.append(Paragraph("Resumen General", heading_style))

    summary_data = [
        ['Métrica', 'Valor'],
        ['Total de mensajes analizados', str(report.total_messages)],
        ['Mensajes neutrales', f"{report.neutral_count} ({report.neutral_percentage:.1f}%)"],
        ['Mensajes positivos', f"{report.positive_count} ({report.positive_percentage:.1f}%)"],
        ['Mensajes de acoso/violencia', f"{report.harassment_count} ({report.harassment_percentage:.1f}%)"],
        ['Mensajes de extorsión', f"{report.extortion_count} ({report.extortion_percentage:.1f}%)"],
    ]

    summary_table = Table(summary_data, colWidths=[3.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 30))

    # Distribución por categoría
    elements.append(Paragraph("Distribución por Categoría", heading_style))

    category_data = [
        ['Categoría', 'Cantidad', 'Porcentaje'],
        ['Neutral', str(report.neutral_count), f"{report.neutral_percentage:.2f}%"],
        ['Positivo', str(report.positive_count), f"{report.positive_percentage:.2f}%"],
        ['Acoso/Violencia', str(report.harassment_count), f"{report.harassment_percentage:.2f}%"],
        ['Extorsión', str(report.extortion_count), f"{report.extortion_percentage:.2f}%"],
    ]

    category_table = Table(category_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    category_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))

    elements.append(category_table)
    elements.append(Spacer(1, 30))

    # Mensajes problemáticos
    problematic_messages = Message.objects.filter(
        conversation=conversation,
        analysis__isnull=False,
        analysis__emotion_label__in=['Acoso/Violencia', 'Extorsión']
    ).select_related('analysis', 'sender')

    if problematic_messages.exists():
        elements.append(Paragraph(f"Mensajes Problemáticos ({problematic_messages.count()})", heading_style))

        for message in problematic_messages[:20]:  # Limitar a 20 mensajes
            message_data = [
                ['Remitente', message.sender.username],
                ['Mensaje', message.content[:200]],  # Limitar a 200 caracteres
                ['Clasificación', message.analysis.emotion_label],
                ['Confianza', f"{message.analysis.confidence:.2f}"],
            ]

            message_table = Table(message_data, colWidths=[1.5*inch, 4*inch])
            message_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))

            elements.append(message_table)
            elements.append(Spacer(1, 10))

        if problematic_messages.count() > 20:
            elements.append(Paragraph(
                f"<i>... y {problematic_messages.count() - 20} mensajes problemáticos más.</i>",
                styles['Normal']
            ))
    else:
        elements.append(Paragraph("Estado de la Conversación", heading_style))
        elements.append(Paragraph(
            "¡Excelente! No se detectaron mensajes problemáticos en esta conversación.",
            styles['Normal']
        ))

    # Pie de página
    elements.append(Spacer(1, 30))
    footer = Paragraph(
        "<i>Este reporte fue generado automáticamente por el Sistema de Análisis de Sentimientos</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    )
    elements.append(footer)

    # Construir el PDF
    doc.build(elements)

    # Obtener el valor del buffer y escribirlo en la respuesta
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

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