from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import RepairOrder

@receiver(pre_save, sender=RepairOrder)
def restore_stock_on_cancel(sender, instance, **kwargs):
    if not instance.pk:
        # ignore the new order
        return

    previous = RepairOrder.objects.get(pk=instance.pk)
    if previous.status != instance.status:
        # if status change is cancelled/failed then update the status pending/paid 
        if instance.status in ['cancelled', 'failed'] and previous.status in ['pending', 'paid']:
            variant = instance.variant
            variant.stock += 1
            variant.save(update_fields=['stock'])
