from django.contrib import admin
from vendors.models import VendorProfile,ServiceVariant,Service,RepairOrder
# Register your models here.
admin.site.register(VendorProfile)
admin.site.register(ServiceVariant)
admin.site.register(Service)
admin.site.register(RepairOrder)