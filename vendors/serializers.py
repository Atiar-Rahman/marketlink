from rest_framework import serializers
from vendors.models import VendorProfile,ServiceVariant,Service,RepairOrder



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



# repair order seralizer
class RepairOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(read_only=True)
    customer = serializers.StringRelatedField(read_only=True)
    vendor = serializers.StringRelatedField(read_only=True)
    variant = ServiceVariantSerializer(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceVariant.objects.all(),
        source='variant',
        write_only=True
    )

    class Meta:
        model = RepairOrder
        fields = [
            'id', 'order_id', 'customer', 'vendor', 'variant', 'variant_id',
            'status', 'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_id', 'customer', 'vendor', 'variant', 'status', 'total_amount', 'created_at', 'updated_at']
  
    def create(self, validated_data):
        request = self.context.get('request')
        customer = request.user if request else None
        variant = validated_data.pop('variant')

        vendor = variant.service.vendor

        total_amount = variant.price

        repair_order = RepairOrder.objects.create(
            customer=customer,
            vendor=vendor,
            variant=variant,
            total_amount=total_amount,
            **validated_data
        )
        return repair_order


class RepairOrderCreateSerializer(RepairOrderSerializer):
    class Meta(RepairOrderSerializer.Meta):
        fields = ['variant_id'] 
        