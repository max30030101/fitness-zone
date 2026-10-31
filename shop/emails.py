import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from .models import CartItem, Order, Product

logger = logging.getLogger(__name__)


def _send_email(user, subject, template, context, event):
    if not user.email:
        return False
    try:
        message = EmailMultiAlternatives(
            subject,
            render_to_string(template, context),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        return message.send(fail_silently=False) == 1
    except Exception:
        logger.exception("%s email failed for user id %s", event, user.pk)
        return False


def send_order_status_email(order_id, old_status, new_status):
    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Order status email skipped: order id %s no longer exists", order_id)
        return False

    statuses = dict(Order.STATUS)
    context = {
        "name": order.user.first_name or order.user.username,
        "order": order,
        "old_status": statuses.get(old_status, old_status),
        "new_status": statuses.get(new_status, new_status),
        "order_url": f"{settings.SITE_URL.rstrip('/')}{reverse('shop:orders')}",
        "site_name": settings.SITE_NAME,
    }
    return _send_email(
        order.user,
        f"Order #{order.pk} {context['new_status'].lower()} — {settings.SITE_NAME}",
        "emails/order_status.txt",
        context,
        "Order status",
    )


def send_cart_restock_emails(product_id):
    try:
        product = Product.objects.get(pk=product_id, is_active=True, stock__gt=0)
    except Product.DoesNotExist:
        return 0

    sent = 0
    items = CartItem.objects.filter(
        product=product,
        cart__user__email__gt="",
    ).select_related("cart__user")
    for item in items:
        user = item.cart.user
        if _send_email(
            user,
            f"{product.name} is back in stock — {settings.SITE_NAME}",
            "emails/cart_restock.txt",
            {
                "name": user.first_name or user.username,
                "product": product,
                "quantity": item.quantity,
                "product_url": f"{settings.SITE_URL.rstrip('/')}{product.get_absolute_url()}",
                "site_name": settings.SITE_NAME,
            },
            "Cart restock",
        ):
            sent += 1
    return sent
