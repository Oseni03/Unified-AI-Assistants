# Generated by Django 5.0.4 on 2024-06-07 16:00

import django.db.models.deletion
import hashid_field.field
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Integration",
            fields=[
                (
                    "id",
                    hashid_field.field.HashidAutoField(
                        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
                        min_length=7,
                        prefix="",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "thirdparty",
                    models.CharField(
                        choices=[
                            ("google-workspace", "Google Workspace"),
                            ("salesforce", "Salesforce"),
                            ("slack", "Slack"),
                        ],
                        max_length=25,
                    ),
                ),
                ("is_chat_app", models.BooleanField(default=False)),
                ("auth_url", models.URLField()),
                ("token_url", models.URLField()),
                ("scope", models.CharField(max_length=255)),
                ("access_token", models.CharField(max_length=255)),
                (
                    "webhook_url",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
