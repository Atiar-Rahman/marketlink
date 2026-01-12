from rest_framework import viewsets, permissions,status
from vendors.models import VendorProfile, Service, ServiceVariant,RepairOrder
from vendors.serializers import VendorProfileSerializer, ServiceVariantSerializer, ServiceSerializer,RepairOrderSerializer,RepairOrderCreateSerializer
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response


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
    queryset = RepairOrder.objects.all()
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

    