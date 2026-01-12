from rest_framework import viewsets, permissions
from vendors.models import VendorProfile, Service, ServiceVariant
from vendors.serializers import VendorProfileSerializer, ServiceVariantSerializer, ServiceSerializer
from rest_framework.exceptions import PermissionDenied

class VendorProfileViewSet(viewsets.ModelViewSet):
    queryset = VendorProfile.objects.all()
    serializer_class = VendorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
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
