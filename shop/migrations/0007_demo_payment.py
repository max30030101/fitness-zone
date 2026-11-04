

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0006_productstock"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[
    ("cod_due", "Cash on Delivery Due"),
    ("unpaid", "Unpaid"),
    ("pending", "Payment Pending"),
    ("success", "Payment Successful"),
    ("failed", "Payment Failed"),
],
              
                default="cod_due",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="stock_reserved",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cod", "Cash on Delivery"),
                    ("demo_upi", "Demo UPI"),
                    ("demo_card", "Demo Card"),
                    ("demo_netbanking", "Demo Net Banking"),
                ],
                default="cod",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "transaction_id",
                    models.CharField(
                        editable=False,
                        max_length=40,
                        unique=True,
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("demo_upi", "Demo UPI"),
                            ("demo_card", "Demo Card"),
                            ("demo_netbanking", "Demo Net Banking"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("success", "Successful"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("is_demo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="shop.order",
                    ),
                ),
            ],
        ),
    ]




