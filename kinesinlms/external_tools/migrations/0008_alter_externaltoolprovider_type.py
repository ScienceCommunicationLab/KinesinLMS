# Generated by Django 5.0.9 on 2024-11-05 05:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("external_tools", "0007_alter_externaltoolprovider_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="externaltoolprovider",
            name="type",
            field=models.CharField(
                choices=[("BASIC_LTI13", "Basic LTIv1.3"), ("JUPYTER_LAB", "JupyterLab")],
                default="JUPYTER_LAB",
                max_length=50,
            ),
        ),
    ]
