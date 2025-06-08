# test_api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'utils', views.UtilityViewSet, basename='utility')

app_name = 'trip_api'

urlpatterns = [
    path('', include(router.urls)),
]