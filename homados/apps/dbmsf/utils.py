from .models import Session, SessionEvent
from .serializers import SessionEventSerializer


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
