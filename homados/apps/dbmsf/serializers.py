from django.db.models import fields
from homados.contrib.serializerfields import BinaryTextField
from rest_framework import serializers

from .models import (Event, Loot, MetasploitCredentialCore, ModuleResult,
                     Session, SessionEvent, Host)


class SessionSerializer(serializers.ModelSerializer):
    datastore = serializers.JSONField()

    class Meta:
        model = Session
        fields = '__all__'


class HostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Host
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


class MetasploitCredentialCoreSerializer(serializers.ModelSerializer):
    host = serializers.CharField(source='origin.session.host.address')
    sid = serializers.IntegerField(source='origin.session.local_id')
    service = serializers.SerializerMethodField()
    post_reference_name = serializers.CharField(source='origin.post_reference_name')
    private = serializers.CharField(source='private.data')
    private_type = serializers.CharField(source='private.type')
    jtr_format = serializers.CharField(source='private.jtr_format')
    public = serializers.CharField(source='public.username')
    realm_key = serializers.CharField(source='realm.key')
    realm_value = serializers.CharField(source='realm.value')
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    class Meta:
        model = MetasploitCredentialCore
        fields = ('id', 'sid', 'service','host', 'post_reference_name', 'private', 'private_type',
                    'jtr_format', 'public', 'realm_key', 'realm_value', 'created_at', 'updated_at')
    
    def get_service(self, obj):
        logins = obj.cred_logins.all()
        if not logins:
            return ''
        logins_info = set([f'{l.service.port}/{l.service.proto} ({l.service.name})' for l in logins])
        return ', '.join(logins_info)


class EventSerializer(serializers.ModelSerializer):
    info = serializers.JSONField()

    class Meta:
        model = Event
        fields = '__all__'


class LootSerializer(serializers.ModelSerializer):
    data = serializers.JSONField()

    class Meta:
        model = Loot
        exclude = ('path', 'workspace')
        depth = 1
