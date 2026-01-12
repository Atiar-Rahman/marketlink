from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vendors.views import VendorProfileViewSet,ServiceViewSet, ServiceVariantViewSet,RepairOrderViewSet,initiate_payment,payment_success,payment_fail,payment_cancel,sslcommerz_webhook

router = DefaultRouter()
router.register(r'vendor-profiles', VendorProfileViewSet, basename='vendorprofile')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-variants', ServiceVariantViewSet, basename='servicevariant')
router.register(r'repair-order',RepairOrderViewSet,basename='repair-order')

urlpatterns = [
    path('', include(router.urls)),
    path("payment/initiate/", initiate_payment, name="initiate-payment"),
    path("payment/success/", payment_success, name="payment-success"),
    path("payment/fail/", payment_fail, name="payment-fail"),
    path("payment/cancel/", payment_cancel, name="payment-cancel"),
    path('webhooks/payment/', sslcommerz_webhook, name='sslcommerz-webhook'),
]
