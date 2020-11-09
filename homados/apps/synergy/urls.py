from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register(r'chatRecord', views.ChatRecordViewSet, basename='chat_record')


urlpatterns = [
    path('', include(router.urls)),
]
