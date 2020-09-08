from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ModuleViewSet, SessionViewSet, LootViewSet, InfoViewSet, JobViewSet


router = SimpleRouter()
router.register(r'modules', ModuleViewSet)
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'loots', LootViewSet, basename='loot')
router.register(r'infos', InfoViewSet, basename='msfinfo')
router.register(r'jobs', JobViewSet, basename='msfjob')


urlpatterns = [
    path('', include(router.urls)),
]
