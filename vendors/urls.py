from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vendors.views import VendorProfileViewSet #ServiceViewSet, ServiceVariantViewSet

router = DefaultRouter()
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendorprofile')
# router.register(r'services', ServiceViewSet, basename='service')
# router.register(r'service-variants', ServiceVariantViewSet, basename='servicevariant')

urlpatterns = [
    path('', include(router.urls)),
]
