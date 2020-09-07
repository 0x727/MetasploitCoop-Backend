from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import AuthViewSet


router = SimpleRouter()
router.register(r'auth', AuthViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
