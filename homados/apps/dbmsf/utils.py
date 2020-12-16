from .models import ModuleResult, Session, SessionEvent
from .serializers import SessionEventSerializer
from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models.aggregates import Min
from libs.utils import memview_to_str
from dateutil import parser


# deprecated
def get_last_output(sid):
    db_session = Session.objects.filter(local_id=sid).order_by('-id').first()
    if not db_session:
        raise Session.DoesNotExist
    last_event_output = SessionEvent.objects.filter(session=db_session, etype='output').order_by('-id').first()
    last_event_nooutput = SessionEvent.objects.filter(session=db_session, id__lt=last_event_output.id)\
                            .exclude(etype='command').order_by('-id').first()
    events = SessionEvent.objects.filter(id__gt=last_event_nooutput.id, id__lte=last_event_output.id)
    serializer = SessionEventSerializer(events, many=True)
    output = ''
    for item in serializer.data:
        item = dict(item)
        output += item.get('output') or ''
    return output

def get_session_events(session) -> list:
    data = []
    if session.session_events:
        serializer = SessionEventSerializer(session.session_events, many=True)
        data = serializer.data
    return data

def get_module_results(session) -> list:
    data = []
    if session.module_results:
        track_uuids = ModuleResult.objects.values_list('track_uuid', flat=True)
        data = list(ModuleResult.objects.filter(session=session).values('track_uuid').annotate(
            output=StringAgg('output', delimiter='', ordering='id'),
            created_at=Min('created_at'),
            fullname=Min('fullname')
        ))
    for i in data:
        i['output'] = memview_to_str(i['output'])
    return data

def sort_history_key(obj):
    """自定义排序函数"""
    created_at = obj['created_at']
    if isinstance(created_at, str):
        return parser.parse(created_at)
    return created_at