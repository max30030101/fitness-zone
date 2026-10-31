from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("media/products/<path:filename>", views.product_image, name="product_image"),
    path("shop/", views.shop, name="list"),
    path("shop/category/<slug:slug>/", views.shop, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="detail"),
    path("favourites/", views.favourites, name="favourites"),
    path("favourites/toggle/<int:product_id>/", views.favourite_toggle, name="favourite_toggle"),
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("addresses/", views.address_book, name="addresses"),
    path("addresses/<int:address_id>/edit/", views.address_book, name="address_edit"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<int:order_id>/confirmed/", views.order_success, name="order_success"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/notifications/<int:notification_id>/read/", views.order_notification_read, name="order_notification_read"),
    path("orders/<int:order_id>/invoice/", views.order_invoice, name="order_invoice"),
]
