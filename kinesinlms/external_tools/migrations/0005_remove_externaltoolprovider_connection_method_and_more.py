# Generated by Django 5.0.9 on 2024-10-23 05:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("external_tools", "0004_remove_externaltoolprovider_default_target_link_uri"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="externaltoolprovider",
            name="connection_method",
        ),
        migrations.AddField(
            model_name="externaltoolprovider",
            name="api_key",
            field=models.CharField(
                blank=True, help_text="The API key for the external tool.", max_length=200, null=True
            ),
        ),
        migrations.AddField(
            model_name="externaltoolprovider",
            name="api_secret",
            field=models.CharField(
                blank=True, help_text="The API secret for the external tool.", max_length=200, null=True
            ),
        ),
        migrations.AddField(
            model_name="externaltoolprovider",
            name="api_url",
            field=models.URLField(blank=True, help_text="The API endpoint for the external tool.", null=True),
        ),
        migrations.AlterField(
            model_name="externaltoolprovider",
            name="launch_uri",
            field=models.URLField(
                blank=True,
                help_text="The launch (target link) URI for this external tool.This is the URL to launch the tool once the login process is complete.Sometimes this URL is called the 'redirection URI'.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="externaltoolprovider",
            name="type",
            field=models.CharField(
                choices=[
                    ("BASIC_LTI13", "Basic LTIv1.3"),
                    ("MODAL", "Modal.com"),
                    ("JUPYTER_HUB", "Jupyterhub"),
                    ("RENKU", "Renku"),
                ],
                default="JUPYTER_HUB",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="externaltoolprovider",
            name="username_field",
            field=models.CharField(
                blank=True,
                choices=[("USERNAME", "username"), ("EMAIL", "email"), ("ANON_USERNAME", "anonymous username")],
                default="USERNAME",
                help_text="The field in the user model that will be used to identify the user to the tool",
                max_length=50,
                null=True,
            ),
        ),
    ]