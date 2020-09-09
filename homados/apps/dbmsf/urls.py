from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import SessionViewSet, SessionEventViewSet


router = SimpleRouter()
router.register(r'sessions', SessionViewSet)
router.register(r'sessionEvents', SessionEventViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
