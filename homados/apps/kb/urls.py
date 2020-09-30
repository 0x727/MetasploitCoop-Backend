from django.urls import include, path
from rest_framework.routers import SimpleRouter

from kb.views import MsfModuleManualViewSet, TranslationBaseViewSet

router = SimpleRouter()
router.register(r'msfModuleManuals', MsfModuleManualViewSet, basename='msf_module_manual')
router.register(r'translationBases', TranslationBaseViewSet, basename='translation_base')


urlpatterns = [
    path('', include(router.urls)),
]
