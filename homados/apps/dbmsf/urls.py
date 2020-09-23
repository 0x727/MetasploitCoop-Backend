from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import SessionViewSet, SessionEventViewSet, ModuleResultViewSet


router = SimpleRouter()
router.register(r'sessions', SessionViewSet)
router.register(r'sessionEvents', SessionEventViewSet)
router.register(r'moduleResults', ModuleResultViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
