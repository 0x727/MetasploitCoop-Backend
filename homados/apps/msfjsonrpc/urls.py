from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views


router = SimpleRouter()
router.register(r'modules', views.ModuleViewSet)
router.register(r'sessions', views.SessionViewSet, basename='session')
router.register(r'loots', views.LootViewSet, basename='loot')
router.register(r'infos', views.InfoViewSet, basename='msfinfo')
router.register(r'jobs', views.JobViewSet, basename='msfjob')
router.register(r'modConfig', views.ModAutoConfigViewSet, basename='mod_config')
router.register(r'rcScripts', views.ResourceScriptViewSet, basename='resource_script')
router.register(r'route', views.RouteViewSet, basename='session_route')


urlpatterns = [
    path('', include(router.urls)),
]
