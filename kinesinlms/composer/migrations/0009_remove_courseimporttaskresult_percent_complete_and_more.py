# Generated by Django 5.0.9 on 2025-01-05 22:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('composer', '0008_courseimporttaskresult_percent_complete_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseimporttaskresult',
            name='percent_complete',
        ),
        migrations.RemoveField(
            model_name='courseimporttaskresult',
            name='status_message',
        ),
    ]