from django.urls import include, path
from rest_framework.routers import SimpleRouter

from kb.views import (FocusKeywordViewSet, MsfModuleManualViewSet,
                      TranslationBaseViewSet)

router = SimpleRouter()
router.register(r'msfModuleManuals', MsfModuleManualViewSet, basename='msf_module_manual')
router.register(r'translationBases', TranslationBaseViewSet, basename='translation_base')
router.register(r'focusKeywords', FocusKeywordViewSet, basename='focus_keyword')


urlpatterns = [
    path('', include(router.urls)),
]
