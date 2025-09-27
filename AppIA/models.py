from django.db import models
from django.contrib.auth.models import User

# MODELOS DEL CHAT

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
    
    def __str__(self):
        return f"Conversación {self.id}"
    
    def get_other_participant(self, user):
        """Obtiene el otro participante de la conversación"""
        return self.participants.exclude(id=user.id).first()
    
    def last_message(self):
        """Obtiene el último mensaje de la conversación"""
        return self.messages.order_by('-created_at').first()

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name='Conversación'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        verbose_name='Remitente'
    )
    content = models.TextField(verbose_name='Contenido del mensaje')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de envío')
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}..."
    

# AGREGAR AL FINAL DE AppIA/models.py (después de las clases Message y Conversation)

class MessageAnalysis(models.Model):
    message = models.OneToOneField(
        Message, 
        on_delete=models.CASCADE, 
        related_name='analysis'
    )
    emotion_label = models.CharField(max_length=50)  # Neutral, Positivo, Acoso/Violencia, Extorsión
    confidence = models.FloatField()  # 0.0 a 1.0
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Análisis de Mensaje'
        verbose_name_plural = 'Análisis de Mensajes'
    
    def __str__(self):
        return f"Análisis: {self.message.sender.username} - {self.emotion_label}"

class ConversationAnalysisReport(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='analysis_reports'
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Estadísticas calculadas
    total_messages = models.IntegerField()
    neutral_count = models.IntegerField(default=0)
    positive_count = models.IntegerField(default=0)
    harassment_count = models.IntegerField(default=0)
    extortion_count = models.IntegerField(default=0)
    
    # Porcentajes
    neutral_percentage = models.FloatField(default=0.0)
    positive_percentage = models.FloatField(default=0.0)
    harassment_percentage = models.FloatField(default=0.0)
    extortion_percentage = models.FloatField(default=0.0)
    
    class Meta:
        verbose_name = 'Reporte de Análisis'
        verbose_name_plural = 'Reportes de Análisis'
        ordering = ['-created_at']
    
    def __str__(self):
        participants = ", ".join([user.username for user in self.conversation.participants.all()])
        return f"Reporte: {participants} - {self.created_at.strftime('%d/%m/%Y')}"