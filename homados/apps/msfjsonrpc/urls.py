from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ModuleViewSet


router = SimpleRouter()
router.register(r'modules', ModuleViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
