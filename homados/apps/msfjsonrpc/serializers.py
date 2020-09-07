from rest_framework import serializers
from .models import Modules


class ModuleSerializer(serializers.ModelSerializer):
    aliases = serializers.ListField()
    author = serializers.ListField()
    references = serializers.ListField()
    targets = serializers.ListField()
    class Meta:
        model = Modules
        exclude = ['info_html', 'compatible_payloads']
