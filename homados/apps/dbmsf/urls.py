from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (EventViewSet, LootViewSet, MetasploitCredentialCoreViewSet,
                    ModuleResultViewSet, SessionEventViewSet, SessionViewSet, HostViewSet)

router = SimpleRouter()
router.register(r'sessions', SessionViewSet)
router.register(r'sessionEvents', SessionEventViewSet)
router.register(r'moduleResults', ModuleResultViewSet)
router.register(r'creds', MetasploitCredentialCoreViewSet)
router.register(r'events', EventViewSet)
router.register(r'loots', LootViewSet)
router.register(r'hosts', HostViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
