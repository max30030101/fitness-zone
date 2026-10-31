from django.conf import settings
from django.db.models import Sum

from .models import CartItem, Category, Favourite, OrderStatusNotification


def shop_globals(request):
    main, _, accent = settings.SITE_NAME.rpartition(" ")
    if not main:  # one-word name
        main, accent = settings.SITE_NAME, ""
    ctx = {"site_name": settings.SITE_NAME, "announcement": settings.ANNOUNCEMENT_TEXT, "brand_main": main, "brand_accent": accent, "nav_categories": Category.objects.all()[:6], "cart_count": 0, "fav_ids": set(), "fav_count": 0, "order_notification_count": 0, "support_email": settings.EMAIL_HOST_USER}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        ctx["cart_count"] = CartItem.objects.filter(cart__user=user).aggregate(n=Sum("quantity"))["n"] or 0
        ids = set(Favourite.objects.filter(user=user).values_list("product_id", flat=True))
        ctx["fav_ids"] = ids
        ctx["fav_count"] = len(ids)
        ctx["order_notification_count"] = OrderStatusNotification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).count()
    return ctx
