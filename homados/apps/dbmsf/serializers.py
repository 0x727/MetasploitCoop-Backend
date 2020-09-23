from rest_framework import serializers
from .models import ModuleResult, Session, SessionEvent, ModuleResult
from homados.contrib.serializerfields import BinaryTextField


class SessionSerializer(serializers.ModelSerializer):
    datastore = serializers.JSONField()

    class Meta:
        model = Session
        fields = '__all__'


class SessionEventSerializer(serializers.ModelSerializer):
    # session_id = serializers.IntegerField(source='session.pk')
    command = BinaryTextField()
    output = BinaryTextField()

    class Meta:
        model = SessionEvent
        fields = '__all__'
        # exclude = ('session', )


class ModuleResultSerializer(serializers.ModelSerializer):
    output = BinaryTextField()
    sid = serializers.IntegerField(source='session.local_id', allow_null=True)

    class Meta:
        model = ModuleResult
        # fields = '__all__'
        exclude = ('session', )
