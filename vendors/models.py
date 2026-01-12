import uuid
from django.db import models
from django.conf import settings

class VendorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_profile'
    )
    business_name = models.CharField(max_length=255)
    address = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name




# service offered by vendor
class Service(models.Model):
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='services'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} by {self.vendor.business_name}"
    

# ServiceVariant Variants for each service

class ServiceVariant(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    name = models.CharField(max_length=100) # e.g., Basic, Premium, Express
    price = models.DecimalField(max_digits=10,decimal_places=2)
    estimated_minutes = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(0) # number of sumultaneous bookings allowed
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.service.name} - {self.name}"
    


# repareorder created by customer for a serviceVariant

class RepairOrder(models.Model):
    STATUS_CHOICES = [
        ('pending','Pending'),
        ('paid','Paid'),
        ('processing','Processing'),
        ('completed','Completed'),
        ('failed','Failed'),
        ('cancelled','Cancelled'),
    ]

    order_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name = 'repair_orders'
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name='repair_orders'
    )
    variant = models.ForeignKey(
        ServiceVariant,
        on_delete=models.CASCADE,
        related_name='repair_orders'
    )

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    total_amount = models.DecimalField(max_digits=10,decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order {self.order_id} -{self.status}'
    
    class Meta:
        ordering = ['-created_at']

