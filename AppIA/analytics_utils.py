import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import base64
from django.db.models import Count
from datetime import datetime, timedelta

def generate_distribution_chart(analysis_data):
    """Genera gráfico de distribución tipo pie"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    labels = ['Neutral', 'Positivo', 'Acoso/Violencia', 'Extorsión']
    sizes = [
        analysis_data['neutral_count'],
        analysis_data['positive_count'],
        analysis_data['harassment_count'],
        analysis_data['extortion_count']
    ]
    colors = ['#95a5a6', '#27ae60', '#e74c3c', '#8e44ad']
    
    # Filtrar valores cero
    non_zero = [(label, size, color) for label, size, color in zip(labels, sizes, colors) if size > 0]
    if non_zero:
        labels, sizes, colors = zip(*non_zero)
    
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title('Distribución de Sentimientos', fontsize=14, fontweight='bold')
    
    # Convertir a base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def generate_bar_chart(analysis_data):
    """Genera gráfico de barras comparativo"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    categories = ['Neutral', 'Positivo', 'Acoso', 'Extorsión']
    values = [
        analysis_data['neutral_count'],
        analysis_data['positive_count'],
        analysis_data['harassment_count'],
        analysis_data['extortion_count']
    ]
    colors = ['#95a5a6', '#27ae60', '#e74c3c', '#8e44ad']
    
    bars = ax.bar(categories, values, color=colors, edgecolor='white', linewidth=1.5)
    
    # Agregar valores encima de las barras
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_ylabel('Cantidad de Mensajes', fontsize=12, fontweight='bold')
    ax.set_title('Comparativa por Categorías', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def generate_temporal_chart(all_analyses):
    """Genera gráfico temporal de últimos 7 días"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Preparar datos
    today = datetime.now().date()
    dates = []
    neutral_data = []
    positive_data = []
    harassment_data = []
    extortion_data = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        dates.append(date.strftime('%d/%m'))
        
        day_analyses = all_analyses.filter(analyzed_at__date=date)
        neutral_data.append(day_analyses.filter(emotion_label='Neutral').count())
        positive_data.append(day_analyses.filter(emotion_label='Positivo').count())
        harassment_data.append(day_analyses.filter(emotion_label='Acoso/Violencia').count())
        extortion_data.append(day_analyses.filter(emotion_label='Extorsión').count())
    
    # Graficar líneas
    ax.plot(dates, neutral_data, marker='o', linewidth=2, label='Neutral', color='#95a5a6')
    ax.plot(dates, positive_data, marker='o', linewidth=2, label='Positivo', color='#27ae60')
    ax.plot(dates, harassment_data, marker='o', linewidth=2, label='Acoso', color='#e74c3c')
    ax.plot(dates, extortion_data, marker='o', linewidth=2, label='Extorsión', color='#8e44ad')
    
    ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cantidad de Mensajes', fontsize=12, fontweight='bold')
    ax.set_title('Tendencia Temporal (Últimos 7 días)', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def generate_user_chart(top_users_data):
    """Genera gráfico horizontal de usuarios más activos"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    usernames = [item['username'] for item in top_users_data]
    counts = [item['count'] for item in top_users_data]
    
    bars = ax.barh(usernames, counts, color='#3498db', edgecolor='white', linewidth=1.5)
    
 
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                f'{int(width)}',
                ha='left', va='center', fontweight='bold', fontsize=10)
    
    ax.set_xlabel('Mensajes Analizados', fontsize=12, fontweight='bold')
    ax.set_title('Top 5 Usuarios Más Activos', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"