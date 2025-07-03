# trip_api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'utils', views.UtilityViewSet, basename='utility')
router.register(r'eld-logs', views.ELDLogViewSet, basename='eld-log')

app_name = 'trip_api'

urlpatterns = [
    path('', include(router.urls)),

    path('driver/current-status/', views.CurrentDriverStatusView.as_view(), name='driver-current-status'),
    path('driver/update-status/', views.DriverStatusUpdateView.as_view(), name='update-driver-status'),
]