from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import AuthViewSet, LogViewSet


router = SimpleRouter()
router.register(r'auth', AuthViewSet)
router.register(r'logs', LogViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
