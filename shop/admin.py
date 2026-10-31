from datetime import timedelta

from django.contrib import admin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import format_html

from .invoices import build_invoice_pdf
from .models import (
    AdminShopNotification,
    Cart,
    CartItem,
    Category,
    Favourite,
    Order,
    OrderItem,
    Product,
    ProductStock,
)


def order_notifications(request):
    can_view_orders = request.user.has_perm("shop.view_order") or request.user.has_perm("shop.change_order")
    can_view_products = request.user.has_perm("shop.view_product") or request.user.has_perm("shop.change_product")
    event_types = []
    if can_view_orders:
        event_types.extend(["new_order", "order_cancelled"])
    if can_view_products:
        event_types.append("product_out_of_stock")
    if not event_types:
        return JsonResponse({"notifications": [], "checked_at": timezone.now().isoformat()})

    since = parse_datetime(request.GET.get("since", ""))
    if since is None:
        return JsonResponse({"error": "A valid since timestamp is required."}, status=400)
    if timezone.is_naive(since):
        since = timezone.make_aware(since, timezone.get_current_timezone())
    since = max(since, timezone.now() - timedelta(days=7))

    events = AdminShopNotification.objects.filter(
        created_at__gt=since,
        event_type__in=event_types,
    ).select_related("order", "product").order_by("created_at", "pk")[:50]
    notifications = []
    for event in events:
        if event.event_type == "new_order":
            message = (
                f"New order #{event.order_id} placed by {event.order.full_name}"
                if event.order_id
                else "A new order was placed"
            )
            url = reverse("admin:shop_order_change", args=[event.order_id]) if event.order_id else reverse("admin:index")
        elif event.event_type == "order_cancelled":
            message = f"Order #{event.order_id} was cancelled" if event.order_id else "An order was cancelled"
            url = reverse("admin:shop_order_change", args=[event.order_id]) if event.order_id else reverse("admin:index")
        else:
            product_name = event.product.name if event.product else "A product"
            message = f"{product_name} is out of stock"
            url = (
                reverse("admin:shop_product_change", args=[event.product_id])
                if event.product_id
                else reverse("admin:index")
            )
        notifications.append({
            "id": event.pk,
            "event_type": event.event_type,
            "message": message,
            "url": url,
        })
    return JsonResponse({"notifications": notifications, "checked_at": timezone.now().isoformat()})


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "position")
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "price", "discount_price", "stock", "is_active", "is_featured")
    list_editable = ("price", "discount_price", "stock", "is_active", "is_featured")
    list_filter = ("category", "is_active", "is_featured", "brand")
    search_fields = ("name", "brand", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_per_page = 30
    actions = ["feature", "unfeature", "deactivate"]

    @admin.action(description="Mark selected as featured")
    def feature(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove featured flag")
    def unfeature(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="Hide selected from the shop")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "discount_price", "stock")
    list_display_links = None
    list_editable = ("price", "discount_price", "stock")
    list_filter = ("category",)
    search_fields = ("name", "brand")
    list_per_page = 1000
    list_max_show_all = 1000

    def has_module_permission(self, request):
        return request.user.has_perm("shop.view_product") or request.user.has_perm("shop.change_product")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("shop.view_product") or request.user.has_perm("shop.change_product")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("shop.change_product")

    def has_add_permission(self, request):
        return request.user.has_perm("shop.add_product")

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:shop_product_add")

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "city", "total", "payment_method", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "created_at", "state")
    search_fields = ("id", "user__username", "user__email", "full_name", "phone", "pincode")
    readonly_fields = ("user", "subtotal", "shipping", "total", "created_at", "invoice_download")
    inlines = [OrderItemInline]
    actions = ["mark_confirmed", "mark_shipped", "mark_delivered", "cancel_and_restock"]

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/invoice/",
                self.admin_site.admin_view(self.invoice_view),
                name="shop_order_invoice",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="Invoice")
    def invoice_download(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse("admin:shop_order_invoice", args=[obj.pk])
        return format_html('<a class="button" href="{}">Download invoice (PDF)</a>', url)

    def invoice_view(self, request, object_id):
        try:
            order = Order.objects.prefetch_related("items").get(pk=object_id)
        except (Order.DoesNotExist, ValueError):
            raise Http404
        if not self.has_view_or_change_permission(request, order):
            raise Http404
        return build_invoice_pdf(order)

    def _set_status(self, queryset, status):
        for order in queryset.iterator():
            if order.status != status:
                order.status = status
                order.save(update_fields=["status"])

    @admin.action(description="Mark as confirmed")
    def mark_confirmed(self, request, queryset):
        self._set_status(queryset, "confirmed")

    @admin.action(description="Mark as shipped")
    def mark_shipped(self, request, queryset):
        self._set_status(queryset, "shipped")

    @admin.action(description="Mark as delivered")
    def mark_delivered(self, request, queryset):
        self._set_status(queryset, "delivered")

    @admin.action(description="Cancel selected orders and return items to stock")
    def cancel_and_restock(self, request, queryset):
        for order in queryset.exclude(status="cancelled"):
            for item in order.items.all():
                if item.product_id:
                    product = Product.objects.get(pk=item.product_id)
                    product.stock += item.quantity
                    product.save(update_fields=["stock"])
            order.status = "cancelled"
            order.save(update_fields=["status"])


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    inlines = [CartItemInline]


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    list_filter = ("created_at",)
