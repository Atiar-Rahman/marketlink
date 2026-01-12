from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vendors.views import VendorProfileViewSet,ServiceViewSet, ServiceVariantViewSet,RepairOrderViewSet

router = DefaultRouter()
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendorprofile')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-variants', ServiceVariantViewSet, basename='servicevariant')
router.register(r'repair-order',RepairOrderViewSet,basename='repair-order')

urlpatterns = [
    path('', include(router.urls)),
]
