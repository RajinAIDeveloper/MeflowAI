from django.db import models
from pgvector.django import VectorField


class KnowledgeDocument(models.Model):
    class DocType(models.TextChoices):
        DOCTOR_PROFILE = 'doctor_profile', 'Doctor Profile'
        HOSPITAL_POLICY = 'hospital_policy', 'Hospital Policy'
        MEDICAL_FAQ = 'medical_faq', 'Medical FAQ'
        DEPARTMENT_INFO = 'department_info', 'Department Info'

    title = models.CharField(max_length=300)
    content = models.TextField()
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    source_id = models.CharField(max_length=100, blank=True, help_text='e.g. doctor pk or policy slug')
    # bge-large-en-v1.5 produces 1024-dimensional vectors
    # (keep in sync with settings.EMBEDDING_DIMENSIONS; changing it needs a migration)
    embedding = VectorField(dimensions=1024, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'knowledge_documents'
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.doc_type}] {self.title}"
