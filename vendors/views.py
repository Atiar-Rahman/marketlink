from django.http import HttpResponseRedirect
from rest_framework import viewsets, permissions,status
from vendors.models import VendorProfile, Service, ServiceVariant,RepairOrder
from vendors.serializers import VendorProfileSerializer, ServiceVariantSerializer, ServiceSerializer,RepairOrderSerializer,RepairOrderCreateSerializer
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view
from sslcommerz_lib import SSLCOMMERZ
from django.conf import settings as main_settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from vendors.models import RepairOrder

class VendorProfileViewSet(viewsets.ModelViewSet):
    queryset = VendorProfile.objects.all()
    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return VendorProfile.objects.none()
        if user.is_staff:
            return VendorProfile.objects.all()
        return VendorProfile.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class IsVendorOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow only vendors who own the object or admins.
    """

    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_staff:
            return True

        # Vendors can only access their own services/variants
        vendor_profile = getattr(request.user, 'vendor_profile', None)
        if not vendor_profile:
            return False

        # Check ownership by vendor
        if isinstance(obj, Service):
            return obj.vendor == vendor_profile
        elif isinstance(obj, ServiceVariant):
            return obj.service.vendor == vendor_profile

        return False


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Service.objects.none() 
        if user.is_staff:
            # Admin sees all
            return Service.objects.all()

        # Vendor sees only their services
        vendor_profile = getattr(user, 'vendor_profile', None)
        if vendor_profile:
            return Service.objects.filter(vendor=vendor_profile)

        # Other users (customers) see none
        return Service.objects.none()

    def perform_create(self, serializer):
        vendor_profile = getattr(self.request.user, 'vendor_profile', None)
        if not vendor_profile:
            raise PermissionDenied("You are not a vendor.")
        serializer.save(vendor=vendor_profile)

    def perform_update(self, serializer):
        vendor_profile = getattr(self.request.user, 'vendor_profile', None)
        if not vendor_profile:
            raise PermissionDenied("You are not a vendor.")

        # Ensure the vendor stays the same (optional)
        instance = serializer.instance
        if instance.vendor != vendor_profile:
            raise PermissionDenied("You can only update your own services.")

        serializer.save()


class ServiceVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceVariantSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ServiceVariant.objects.none()
        
        if user.is_staff:
            return ServiceVariant.objects.all()

        vendor_profile = getattr(user, 'vendor_profile', None)
        if vendor_profile:
            return ServiceVariant.objects.filter(service__vendor=vendor_profile)

        return ServiceVariant.objects.none()

    def perform_create(self, serializer):
        vendor_profile = getattr(self.request.user, 'vendor_profile', None)
        if not vendor_profile:
            raise PermissionDenied("You are not a vendor.")

        service = serializer.validated_data.get('service')
        if not service or service.vendor != vendor_profile:
            raise PermissionDenied("You can only add variants to your own services.")

        serializer.save()

    def perform_update(self, serializer):
        vendor_profile = getattr(self.request.user, 'vendor_profile', None)
        if not vendor_profile:
            raise PermissionDenied("You are not a vendor.")

        # Get service from updated data or existing instance
        service = serializer.validated_data.get('service', serializer.instance.service)
        if not service or service.vendor != vendor_profile:
            raise PermissionDenied("You can only update variants of your own services.")

        serializer.save()


class RepairOrderViewSet(viewsets.ModelViewSet):
    serializer_class = RepairOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return RepairOrder.objects.none()
        if user.is_staff:
            return RepairOrder.objects.all()
        return RepairOrder.objects.filter(customer=user)

    @swagger_auto_schema(request_body=RepairOrderCreateSerializer)
    def create(self, request, *args, **kwargs):
        serializer = RepairOrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        variant = serializer.validated_data['variant']
        lock_key = f"variant_lock_{variant.id}"

        try:
            with cache.lock(lock_key, timeout=10, blocking_timeout=5):
                with transaction.atomic():
                    variant.refresh_from_db()
                    if variant.stock <= 0:
                        raise ValidationError({"variant": "No stock available for this service variant."})
                    variant.stock -= 1
                    variant.save(update_fields=["stock"])
                    repair_order = RepairOrder.objects.create(
                        customer=request.user,
                        vendor=variant.service.vendor,
                        variant=variant,
                        total_amount=variant.price,
                        status="pending"
                    )
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError({"detail": f"Unexpected error: {str(e)}"})

        output_serializer = RepairOrderSerializer(repair_order)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)



@api_view(['POST'])
def initiate_payment(request):
    user = request.user
    amount = request.data.get("amount")
    order_id = request.data.get("orderId")
    settings = {
        'store_id': main_settings.SSLC_STORE_ID,
        'store_pass': main_settings.SSLC_STORE_PASS,
        'issandbox': main_settings.SSLC_IS_SANDBOX,
    }
    settings = {'store_id': 'phima67ddc8dba290b',
                'store_pass': 'phima67ddc8dba290b@ssl', 'issandbox': True}
    sslcz = SSLCOMMERZ(settings)
    post_body = {}
    post_body['total_amount'] = amount
    post_body['currency'] = "BDT"
    post_body['tran_id'] = f"txn_{order_id}"
    post_body['success_url'] = f"{main_settings.BACKEND_URL}/api/v1/payment/success/"
    post_body['fail_url'] = f"{main_settings.BACKEND_URL}/api/v1/payment/fail/"
    post_body['cancel_url'] = f"{main_settings.BACKEND_URL}/api/v1/payment/cancel/"
    post_body['emi_option'] = 0
    post_body['cus_name'] = f"{user.first_name} {user.last_name}"
    post_body['cus_email'] = user.email
    post_body['cus_phone'] = user.phone_number
    post_body['cus_add1'] = user.address
    post_body['cus_city'] = "Dhaka"
    post_body['cus_country'] = "Bangladesh"
    post_body['shipping_method'] = "No"
    post_body['multi_card_name'] = ""
    post_body['num_of_item'] = ""
    post_body['product_name'] = "E-commerce Products"
    post_body['product_category'] = "General"
    post_body['product_profile'] = "general"

    response = sslcz.createSession(post_body)  # API response

    if response.get("status") == 'SUCCESS':
        return Response({"payment_url": response['GatewayPageURL']})
    return Response({"error": "Payment initiation failed"}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
def payment_success(request):
    print("Inside success")
    order_id = request.data.get("tran_id").split('_')[1]
    order = RepairOrder.objects.get(order_id=order_id)
    order.status = "paid"
    order.save()
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")


@api_view(['POST'])
def payment_cancel(request):
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")


@api_view(['POST'])
def payment_fail(request):
    print("Inside fail")
    return HttpResponseRedirect(f"{main_settings.FRONTEND_URL}/dashboard/orders/")




@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def sslcommerz_webhook(request):
    # SSLCommerz sends JSON or form data, get data
    data = request.data

    # Verify the webhook signature if provided (depends on SSLCommerz docs)
    # Example: if a signature header or key is sent, verify here.
    # For demo, assuming a secret key and signature check:
    webhook_secret = main_settings.WEBHOOK_SECRET  # set this in your env
    
    received_signature = request.headers.get('X-SSLCommerz-Signature')  # hypothetical header
    # Calculate HMAC or other signature here according to SSLCommerz docs
    
    # For example purposes, let's assume this:
    # message = json.dumps(data, separators=(',', ':'), sort_keys=True).encode()
    # expected_signature = hmac.new(webhook_secret.encode(), message, hashlib.sha256).hexdigest()
    # if not hmac.compare_digest(received_signature, expected_signature):
    #     return Response({"detail": "Invalid signature"}, status=400)

    # Idempotency check: you need to store event_ids in DB or cache to prevent double processing
    event_id = data.get('event_id')  # depends on actual payload
    tran_id = data.get('tran_id')  # transaction id, e.g., "txn_orderid"

    # Extract your order id from tran_id
    if not tran_id or not tran_id.startswith('txn_'):
        return Response({"detail": "Invalid transaction ID"}, status=400)

    order_id = tran_id.split('txn_')[-1]

    try:
        order = RepairOrder.objects.get(id=order_id)
    except RepairOrder.DoesNotExist:
        return Response({"detail": "Order not found"}, status=404)

    # Verify amount matches
    paid_amount = data.get('amount')  # or 'total_amount', depends on webhook payload key
    if str(order.total_amount) != str(paid_amount):
        return Response({"detail": "Amount mismatch"}, status=400)

    # Check if order already paid (idempotent)
    if order.status == 'paid':
        return Response({"detail": "Order already paid"}, status=200)

    # Mark order paid and trigger post-payment actions
    order.status = 'paid'
    order.save()

    # TODO: enqueue background job for invoice email, processing etc.

    return Response({"detail": "Payment confirmed"}, status=200)