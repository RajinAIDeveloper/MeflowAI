from django.contrib import admin

from .models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'doc_type', 'source_id', 'updated_at')
    list_filter = ('doc_type',)
    search_fields = ('title', 'content')
    readonly_fields = ('embedding', 'created_at', 'updated_at')
