from rest_framework import serializers

from .models import KnowledgeDocument


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = ('id', 'title', 'content', 'doc_type', 'source_id',
                  'metadata', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class IngestRequestSerializer(serializers.Serializer):
    title = serializers.CharField()
    content = serializers.CharField()
    doc_type = serializers.ChoiceField(choices=KnowledgeDocument.DocType.choices)
    source_id = serializers.CharField(required=False, default='')
    metadata = serializers.DictField(required=False, default=dict)


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField()
    doc_type = serializers.ChoiceField(
        choices=KnowledgeDocument.DocType.choices, required=False
    )
    top_k = serializers.IntegerField(min_value=1, max_value=20, default=5)


class SearchResultSerializer(serializers.ModelSerializer):
    distance = serializers.FloatField(read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = ('id', 'title', 'content', 'doc_type', 'source_id', 'metadata', 'distance')
