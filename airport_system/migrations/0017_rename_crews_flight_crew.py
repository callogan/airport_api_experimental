# Generated by Django 5.0.1 on 2024-03-04 11:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0016_alter_route_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="flight",
            old_name="crews",
            new_name="crew",
        ),
    ]
