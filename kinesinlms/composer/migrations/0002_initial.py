# Generated by Django 5.0.6 on 2024-08-05 10:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("composer", "0001_initial"),
        ("course", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="composersettings",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="composer_settings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="editstatus",
            name="course",
            field=models.OneToOneField(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name="edit_status", to="course.course"
            ),
        ),
    ]
