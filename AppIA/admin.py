from django.contrib import admin

# Register your models here.# AGREGAR ESTAS LÍNEAS AL FINAL DE TU ARCHIVO AppIA/admin.py
# (Mantén todo tu código existente arriba)

from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__username', 'participants__first_name', 'participants__last_name')
    filter_horizontal = ('participants',)
    
    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participantes'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'content_preview', 'created_at')
    list_filter = ('created_at', 'sender')
    search_fields = ('content', 'sender__username', 'conversation__id')
    readonly_fields = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenido'
