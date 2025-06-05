# test_api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

app_name = 'trip_api'

urlpatterns = [
    path('', include(router.urls)),
]