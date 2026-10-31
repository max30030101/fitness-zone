from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AdminShopNotification,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    OrderStatusNotification,
    Product,
    SavedAddress,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_NAME="Fitness Zone",
    SITE_URL="https://example.test",
)
class ShopNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.test",
            password="test-password",
            first_name="Casey",
        )
        self.category = Category.objects.create(name="Training")
        self.product = Product.objects.create(
            category=self.category,
            name="Training Mat",
            price="25.00",
            stock=0,
        )

    def make_order(self, user=None):
        return Order.objects.create(
            user=user or self.user,
            full_name="Casey Customer",
            phone="1234567890",
            address_line="1 Main Street",
            city="Test City",
            state="Test State",
            pincode="123456",
        )

    def test_order_status_change_sends_email_after_commit(self):
        order = self.make_order()

        with self.captureOnCommitCallbacks(execute=True):
            order.status = "shipped"
            order.save(update_fields=["status"])

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.test"])
        self.assertIn("shipped", mail.outbox[0].subject.lower())
        self.assertIn("changed from Pending to Shipped", mail.outbox[0].body)
        self.assertIn("https://example.test", mail.outbox[0].body)
        notification = OrderStatusNotification.objects.get(order=order)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.old_status, "pending")
        self.assertEqual(notification.new_status, "shipped")

    def test_orders_page_shows_and_marks_status_notifications_read(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = "confirmed"
            order.save(update_fields=["status"])

        notification = OrderStatusNotification.objects.get(order=order)
        self.assertIsNone(notification.read_at)
        self.client.force_login(self.user)

        response = self.client.get(reverse("shop:orders"))

        self.assertContains(response, "Order updates")
        self.assertContains(response, "changed from Pending to")
        self.assertContains(response, "Confirmed")
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_home_page_shows_latest_unread_order_status_popup(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = "shipped"
            order.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertContains(response, 'id="home-order-notification"')
        self.assertContains(response, "Order update")
        self.assertContains(response, "changed from Pending to")
        self.assertContains(response, "Shipped")
        self.assertContains(response, reverse("shop:order_notification_read", args=[
            OrderStatusNotification.objects.get(order=order).pk,
        ]))

    def test_closing_home_popup_marks_only_owned_notification_read(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = "cancelled"
            order.save(update_fields=["status"])
        notification = OrderStatusNotification.objects.get(order=order)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("shop:order_notification_read", args=[notification.pk]),
        )

        self.assertRedirects(response, reverse("home"))
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_user_cannot_dismiss_another_users_order_notification(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = "shipped"
            order.save(update_fields=["status"])
        notification = OrderStatusNotification.objects.get(order=order)
        other_user = User.objects.create_user(
            username="notification-owner-check",
            email="notification-owner-check@example.test",
            password="test-password",
        )
        self.client.force_login(other_user)

        response = self.client.post(
            reverse("shop:order_notification_read", args=[notification.pk]),
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)

    def test_order_updates_badge_counts_only_current_users_unread_notifications(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = "shipped"
            order.save(update_fields=["status"])
        other_user = User.objects.create_user(
            username="other-customer",
            email="other@example.test",
            password="test-password",
        )
        other_order = self.make_order(user=other_user)
        with self.captureOnCommitCallbacks(execute=True):
            other_order.status = "confirmed"
            other_order.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("shop:cart"))

        self.assertContains(response, 'aria-label="Your orders, 1 unread updates"')
        self.assertContains(response, "Your orders")

    def test_orders_menu_tab_is_only_visible_to_authenticated_users(self):
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, ">Your orders</a>")

        self.client.force_login(self.user)
        response = self.client.get(reverse("shop:orders"))

        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, "Your orders")

    def test_unchanged_order_status_does_not_send_email(self):
        order = self.make_order()

        with self.captureOnCommitCallbacks(execute=True):
            order.save(update_fields=["status"])

        self.assertEqual(mail.outbox, [])


    def test_unsaved_status_change_does_not_send_email(self):
        order = self.make_order()
        order.status = "shipped"

        with self.captureOnCommitCallbacks(execute=True):
            order.save(update_fields=["full_name"])

        self.assertEqual(mail.outbox, [])

    def test_restock_emails_users_who_have_product_in_cart(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.stock = 5
            self.product.save(update_fields=["stock"])

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.test"])
        self.assertIn("back in stock", mail.outbox[0].subject.lower())
        self.assertIn("Training Mat is back in stock", mail.outbox[0].body)
        self.assertIn("You have 2 in your cart", mail.outbox[0].body)
        self.assertIn("https://example.test/product/training-mat/", mail.outbox[0].body)

    def test_restock_does_not_email_when_product_was_already_available(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.product.stock = 3
        self.product.save(update_fields=["stock"])
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            self.product.stock = 5
            self.product.save(update_fields=["stock"])

        self.assertEqual(mail.outbox, [])

    def test_unsaved_stock_change_does_not_send_email(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.product.stock = 5

        with self.captureOnCommitCallbacks(execute=True):
            self.product.save(update_fields=["name"])

        self.assertEqual(mail.outbox, [])


class OrderInvoiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="invoice-customer",
            email="invoice@example.test",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-customer",
            email="other@example.test",
            password="test-password",
        )
        self.order = Order.objects.create(
            user=self.user,
            full_name="Invoice Customer",
            phone="1234567890",
            address_line="1 Main Street",
            city="Test City",
            state="Test State",
            pincode="123456",
            subtotal="50.00",
            shipping="5.00",
            total="55.00",
        )
        OrderItem.objects.create(
            order=self.order,
            product_name="Training Mat",
            unit_price="25.00",
            quantity=2,
        )

    def add_product_to_order(self, stock=3, quantity=2):
        category = Category.objects.create(name="Invoice Training")
        product = Product.objects.create(
            category=category,
            name="Invoice Mat",
            price="25.00",
            stock=stock,
        )
        OrderItem.objects.create(
            order=self.order,
            product=product,
            product_name=product.name,
            unit_price="25.00",
            quantity=quantity,
        )
        return product

    def test_customer_can_download_own_order_invoice(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("shop:order_invoice", args=[self.order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="order-{self.order.pk}-invoice.pdf"',
        )
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_customer_cannot_download_another_users_invoice(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("shop:order_invoice", args=[self.order.pk]))

        self.assertEqual(response.status_code, 404)

    def test_order_success_and_list_link_to_invoice(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("shop:orders"))

        self.assertContains(response, reverse("shop:order_invoice", args=[self.order.pk]))
        response = self.client.get(reverse("shop:order_success", args=[self.order.pk]))
        self.assertContains(response, reverse("shop:order_invoice", args=[self.order.pk]))
        self.assertContains(response, 'id="order-confirmation"')
        self.assertContains(response, 'aria-label="Close order confirmation"')
        self.assertContains(response, "Thanks for your order!")
        dialog = response.content.decode().split('<dialog id="order-confirmation"', 1)[1].split("</dialog>", 1)[0]
        self.assertIn(">View order</a>", dialog)
        self.assertIn('method="dialog"', dialog)
        self.assertNotIn("Download invoice (PDF)", dialog)
        self.assertNotIn("Continue shopping", dialog)

    def test_admin_can_download_invoice_from_order_view(self):
        admin_user = User.objects.create_superuser(
            username="invoice-admin",
            email="admin@example.test",
            password="test-password",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:shop_order_change", args=[self.order.pk]))
        invoice_url = reverse("admin:shop_order_invoice", args=[self.order.pk])
        self.assertContains(response, invoice_url)
        self.assertContains(response, "Download invoice (PDF)")

        response = self.client.get(invoice_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_admin_invoice_download_requires_staff_access(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("admin:shop_order_invoice", args=[self.order.pk]))

        self.assertEqual(response.status_code, 302)

    def test_customer_can_cancel_pending_order_and_stock_is_restored(self):
        product = self.add_product_to_order()
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("shop:order_cancel", args=[self.order.pk]))

        self.assertRedirects(response, reverse("shop:orders"))
        self.order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")
        self.assertEqual(product.stock, 5)
        self.assertTrue(OrderStatusNotification.objects.filter(
            order=self.order,
            old_status="pending",
            new_status="cancelled",
        ).exists())

    def test_customer_can_cancel_confirmed_order(self):
        self.order.status = "confirmed"
        self.order.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.post(reverse("shop:order_cancel", args=[self.order.pk]))

        self.assertRedirects(response, reverse("shop:orders"))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "cancelled")

    def test_customer_cannot_cancel_shipped_order(self):
        product = self.add_product_to_order()
        self.order.status = "shipped"
        self.order.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.post(reverse("shop:order_cancel", args=[self.order.pk]))

        self.assertRedirects(response, reverse("shop:orders"))
        self.order.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")
        self.assertEqual(product.stock, 3)

    def test_customer_cannot_cancel_another_users_order(self):
        self.client.force_login(self.other_user)

        response = self.client.post(reverse("shop:order_cancel", args=[self.order.pk]))

        self.assertEqual(response.status_code, 404)

    def test_cancel_option_only_shows_before_shipping(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("shop:orders"))
        self.assertContains(response, reverse("shop:order_cancel", args=[self.order.pk]))

        self.order.status = "shipped"
        self.order.save(update_fields=["status"])
        response = self.client.get(reverse("shop:orders"))
        self.assertNotContains(response, reverse("shop:order_cancel", args=[self.order.pk]))


class CheckoutAddressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="address-customer",
            email="address-customer@example.test",
            password="test-password",
            first_name="Checkout Customer",
        )
        self.category = Category.objects.create(name="Address checkout")
        self.product = Product.objects.create(
            category=self.category,
            name="Address test item",
            price="20.00",
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def make_address(self, user=None, **overrides):
        values = {
            "user": user or self.user,
            "label": "Home",
            "full_name": "Checkout Customer",
            "phone": "9876543210",
            "address_line": "12 Green Road",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
        }
        values.update(overrides)
        return SavedAddress.objects.create(**values)

    def test_checkout_lists_saved_addresses_and_prefills_selected_address(self):
        address = self.make_address()
        self.client.force_login(self.user)

        response = self.client.get(reverse("shop:checkout"))

        self.assertContains(response, f'value="{address.pk}"')
        self.assertContains(response, "Home — 12 Green Road, Pune")
        self.assertContains(response, 'data-address-line="12 Green Road"')
        self.assertContains(response, 'name="saved_address"')

    def test_checkout_saves_new_address_by_default(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("shop:checkout"))

        self.assertRegex(response.content.decode(), r'name="save_address"[^>]*checked')

    def test_checkout_uses_saved_address_and_can_update_it(self):
        address = self.make_address()
        self.client.force_login(self.user)

        response = self.client.post(reverse("shop:checkout"), {
            "saved_address": str(address.pk),
            "full_name": "",
            "phone": "",
            "address_line": "",
            "city": "",
            "state": "",
            "pincode": "",
            "save_address": "on",
            "address_label": "Office",
        })

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse("shop:order_success", args=[order.pk]))
        self.assertEqual(order.full_name, address.full_name)
        self.assertEqual(order.phone, address.phone)
        self.assertEqual(order.address_line, address.address_line)
        self.assertEqual(order.city, address.city)
        self.assertEqual(order.state, address.state)
        self.assertEqual(order.pincode, address.pincode)
        address.refresh_from_db()
        self.assertEqual(address.label, "Office")

    def test_checkout_can_save_a_new_address_for_later(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("shop:checkout"), {
            "saved_address": "",
            "full_name": "New Recipient",
            "phone": "9876543210",
            "address_line": "50 River Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "save_address": "on",
            "address_label": "Work",
        })

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse("shop:order_success", args=[order.pk]))
        saved = SavedAddress.objects.get(user=self.user, label="Work")
        self.assertEqual(saved.address_line, "50 River Street")
        self.assertEqual(saved.city, "Mumbai")

    def test_user_can_add_and_edit_saved_addresses(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("shop:addresses"), {
            "label": "Apartment",
            "full_name": "Checkout Customer",
            "phone": "9876543210",
            "address_line": "8 Hill Road",
            "city": "Nashik",
            "state": "Maharashtra",
            "pincode": "422001",
        })
        self.assertRedirects(response, reverse("shop:addresses"))
        address = SavedAddress.objects.get(user=self.user, label="Apartment")

        response = self.client.post(reverse("shop:address_edit", args=[address.pk]), {
            "label": "New home",
            "full_name": "Checkout Customer",
            "phone": "9876543210",
            "address_line": "9 Hill Road",
            "city": "Nashik",
            "state": "Maharashtra",
            "pincode": "422001",
        })
        self.assertRedirects(response, reverse("shop:addresses"))
        address.refresh_from_db()
        self.assertEqual(address.label, "New home")
        self.assertEqual(address.address_line, "9 Hill Road")

    def test_user_cannot_edit_another_users_saved_address(self):
        other_user = User.objects.create_user(
            username="address-owner",
            email="address-owner@example.test",
            password="test-password",
        )
        address = self.make_address(user=other_user)
        self.client.force_login(self.user)

        response = self.client.get(reverse("shop:address_edit", args=[address.pk]))

        self.assertEqual(response.status_code, 404)

    def test_checkout_rejects_another_users_saved_address(self):
        other_user = User.objects.create_user(
            username="foreign-address-owner",
            email="foreign-address-owner@example.test",
            password="test-password",
        )
        address = self.make_address(user=other_user)
        self.client.force_login(self.user)

        response = self.client.post(reverse("shop:checkout"), {
            "saved_address": str(address.pk),
            "full_name": address.full_name,
            "phone": address.phone,
            "address_line": address.address_line,
            "city": address.city,
            "state": address.state,
            "pincode": address.pincode,
            "address_label": "Home",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        self.assertContains(response, "Select a valid choice")


class AdminOrderNotificationTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="notification-admin",
            email="notification-admin@example.test",
            password="test-password",
        )
        self.client.force_login(self.admin_user)
        self.endpoint = reverse("admin_order_notifications")

    def test_staff_receives_new_order_notification(self):
        order = Order.objects.create(
            user=self.admin_user,
            full_name="New Customer",
            phone="1234567890",
            address_line="1 Main Street",
            city="Test City",
            state="Test State",
            pincode="123456",
        )
        event = AdminShopNotification.objects.get(event_type="new_order", order=order)
        since = (event.created_at - timedelta(seconds=1)).isoformat()

        response = self.client.get(self.endpoint, {"since": since})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notifications"], [{
            "id": event.pk,
            "event_type": "new_order",
            "message": f"New order #{order.pk} placed by New Customer",
            "url": reverse("admin:shop_order_change", args=[order.pk]),
        }])
        self.assertIn("checked_at", response.json())

    def test_staff_receives_order_cancellation_notification(self):
        order = Order.objects.create(
            user=self.admin_user,
            full_name="Cancelling Customer",
            phone="1234567890",
            address_line="1 Main Street",
            city="Test City",
            state="Test State",
            pincode="123456",
        )
        order.status = "cancelled"
        order.save(update_fields=["status"])
        event = AdminShopNotification.objects.get(event_type="order_cancelled", order=order)
        since = (event.created_at - timedelta(seconds=1)).isoformat()

        response = self.client.get(self.endpoint, {"since": since})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [notification["message"] for notification in response.json()["notifications"]],
            [
                f"New order #{order.pk} placed by Cancelling Customer",
                f"Order #{order.pk} was cancelled",
            ],
        )
        self.assertEqual(
            [notification["event_type"] for notification in response.json()["notifications"]],
            ["new_order", "order_cancelled"],
        )

    def test_staff_receives_product_out_of_stock_notification(self):
        category = Category.objects.create(name="Admin notifications")
        product = Product.objects.create(
            category=category,
            name="Last item",
            price="25.00",
            stock=1,
        )
        product.stock = 0
        product.save(update_fields=["stock"])
        event = AdminShopNotification.objects.get(
            event_type="product_out_of_stock",
            product=product,
        )
        since = (event.created_at - timedelta(seconds=1)).isoformat()

        response = self.client.get(self.endpoint, {"since": since})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notifications"], [{
            "id": event.pk,
            "event_type": "product_out_of_stock",
            "message": "Last item is out of stock",
            "url": reverse("admin:shop_product_change", args=[product.pk]),
        }])

    def test_notification_endpoint_requires_timestamp(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_staff_without_order_permission_gets_no_order_data(self):
        staff_user = User.objects.create_user(
            username="limited-staff",
            email="limited-staff@example.test",
            password="test-password",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(self.endpoint, {"since": timezone.now().isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notifications"], [])

    def test_staff_receives_only_notifications_they_can_access(self):
        limited_staff = User.objects.create_user(
            username="product-staff",
            email="product-staff@example.test",
            password="test-password",
            is_staff=True,
        )
        limited_staff.user_permissions.add(
            Permission.objects.get(codename="view_product", content_type__app_label="shop"),
        )
        category = Category.objects.create(name="Limited staff")
        product = Product.objects.create(
            category=category,
            name="Out of stock item",
            price="15.00",
            stock=0,
        )
        Order.objects.create(
            user=self.admin_user,
            full_name="Private Customer",
            phone="1234567890",
            address_line="1 Main Street",
            city="Test City",
            state="Test State",
            pincode="123456",
        )
        event = AdminShopNotification.objects.get(
            event_type="product_out_of_stock",
            product=product,
        )
        self.client.force_login(limited_staff)

        response = self.client.get(
            self.endpoint,
            {"since": (event.created_at - timedelta(seconds=1)).isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["notifications"]), 1)
        self.assertIn("Out of stock item", response.json()["notifications"][0]["message"])
        self.assertNotIn("Private Customer", str(response.json()["notifications"]))

    def test_admin_pages_load_order_notification_script(self):
        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, "js/admin_order_notifications.js")
        self.assertContains(response, "css/admin_order_notifications.css")
        self.assertContains(response, self.endpoint)


@override_settings(EMAIL_HOST_USER="support@example.test")
class OrderHelpPopupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="help-customer",
            email="help@example.test",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_orders_page_shows_contact_popup_with_configured_email(self):
        response = self.client.get(reverse("shop:orders"))

        self.assertContains(response, 'data-open-dialog="contact-help"')
        self.assertContains(response, 'id="contact-help"')
        self.assertContains(response, "Contact us")
        self.assertContains(response, "mailto:support@example.test")
        self.assertContains(response, "support@example.test")

    @override_settings(EMAIL_HOST_USER="")
    def test_contact_popup_explains_when_support_email_is_not_configured(self):
        response = self.client.get(reverse("shop:orders"))

        self.assertContains(response, "Our support email is not configured yet.")
        self.assertNotContains(response, "mailto:")
