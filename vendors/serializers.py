from rest_framework import serializers
from vendors.models import VendorProfile,ServiceVariant,Service

class VendorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = ['id', 'user', 'business_name', 'address', 'is_active', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate(self, attrs):
        user = self.context['request'].user
        if VendorProfile.objects.filter(user=user).exists():
            raise serializers.ValidationError("You already have a vendor profile.")
        return attrs



# ServiceVariantSerializer
class ServiceVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceVariant
        fields = ['id', 'service', 'name', 'price', 'estimated_minutes', 'stock', 'is_active']




# ServiceSerializer (with nested variants)
class ServiceSerializer(serializers.ModelSerializer):
    variants = ServiceVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'vendor', 'name', 'description', 'is_active', 'created_at', 'variants']
        read_only_fields = ['id','created_at', 'variants']
