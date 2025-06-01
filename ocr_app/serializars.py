from .models import DocumentType,Document
from rest_framework import serializers
class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = '__all__'

class DocumentSerializer(serializers.ModelSerializer):
    type = DocumentTypeSerializer(read_only=True)

    class Meta:
        model = Document
        fields = '__all__'