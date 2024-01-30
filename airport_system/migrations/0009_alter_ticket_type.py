# Generated by Django 5.0.1 on 2024-01-29 16:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0008_alter_ticket_allocated"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ticket",
            name="type",
            field=models.CharField(
                choices=[
                    ("check-in-pending", "Check-in-pending"),
                    ("completed", "Completed"),
                ],
                default="check-in-pending",
                max_length=20,
            ),
        ),
    ]
