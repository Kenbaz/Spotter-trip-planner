from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from . import views


router = DefaultRouter()
router.register(r'', views.UserViewSet, basename='user')
router.register(r'company', views.SpotterCompanyViewSet, basename='company')
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')
router.register(r'assignments', views.DriverVehicleAssignmentViewSet, basename='assignment')

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
     path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('', include(router.urls)),
]