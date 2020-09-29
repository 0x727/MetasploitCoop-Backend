from django.urls import include, path
from rest_framework.routers import SimpleRouter

from kb.views import MsfModuleManualViewSet

router = SimpleRouter()
router.register(r'msfModuleManuals', MsfModuleManualViewSet, basename='msf_module_manual')


urlpatterns = [
    path('', include(router.urls)),
]
