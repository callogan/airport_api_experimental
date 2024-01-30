# Generated by Django 5.0.1 on 2024-01-26 17:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0006_seat_alter_ticket_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="type",
            field=models.CharField(
                choices=[("check-in", "Check-in"), ("prepaid", "Prepaid")],
                default="check-in",
                max_length=20,
            ),
        ),
    ]