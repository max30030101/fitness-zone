from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import send_cart_restock_emails, send_order_status_email
from .models import AdminShopNotification, Order, OrderStatusNotification, Product


def notify_user_order_status_change(order_id, old_status, new_status):
    order = Order.objects.only("pk", "user_id").get(pk=order_id)
    OrderStatusNotification.objects.create(
        user_id=order.user_id,
        order_id=order_id,
        old_status=old_status,
        new_status=new_status,
    )
    send_order_status_email(order_id, old_status, new_status)


@receiver(pre_save, sender=Order)
def remember_order_status(sender, instance, update_fields=None, **kwargs):
    instance._previous_status = None
    instance._status_will_save = update_fields is None or "status" in update_fields
    if instance.pk and instance._status_will_save:
        instance._previous_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(post_save, sender=Order)
def notify_order_status_change(sender, instance, created, **kwargs):
    if created:
        AdminShopNotification.objects.create(event_type="new_order", order=instance)
        return
    previous = getattr(instance, "_previous_status", None)
    if not getattr(instance, "_status_will_save", False) or previous is None or previous == instance.status:
        return
    if instance.status == "cancelled":
        AdminShopNotification.objects.create(event_type="order_cancelled", order=instance)
    order_id, new_status = instance.pk, instance.status
    transaction.on_commit(
        lambda: notify_user_order_status_change(order_id, previous, new_status)
    )


@receiver(pre_save, sender=Product)
def remember_product_stock(sender, instance, update_fields=None, **kwargs):
    instance._previous_stock = None
    instance._stock_will_save = update_fields is None or "stock" in update_fields
    if instance.pk and instance._stock_will_save:
        instance._previous_stock = sender.objects.filter(pk=instance.pk).values_list("stock", flat=True).first()


@receiver(post_save, sender=Product)
def notify_cart_restock(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_stock", None)
    if created and instance.stock == 0:
        AdminShopNotification.objects.create(event_type="product_out_of_stock", product=instance)
        return
    if (
        not created
        and getattr(instance, "_stock_will_save", False)
        and previous is not None
        and previous > 0
        and instance.stock == 0
    ):
        AdminShopNotification.objects.create(event_type="product_out_of_stock", product=instance)
    if created or not getattr(instance, "_stock_will_save", False) or previous is None or previous > 0 or instance.stock <= 0:
        return
    product_id = instance.pk
    transaction.on_commit(lambda: send_cart_restock_emails(product_id))
