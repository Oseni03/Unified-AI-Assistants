# Generated by Django 5.0.4 on 2024-04-29 15:23

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
            name="Agent",
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
                ("name", models.CharField(default="AI assistant", max_length=255)),
                ("access_token", models.CharField(max_length=255)),
                ("refresh_token", models.CharField(max_length=255, null=True)),
                ("token_uri", models.CharField(max_length=255, null=True)),
                ("id_token", models.CharField(max_length=255)),
                (
                    "thirdparty",
                    models.CharField(
                        choices=[
                            ("gmail", "Google Mail"),
                            ("google-calender", "Google Calender"),
                            ("google-document", "Google Document"),
                            ("google-drive", "Google Drive"),
                            ("google-sheet", "Google Sheet"),
                            ("salesforce", "Salesforce"),
                            ("slack", "Slack"),
                        ],
                        max_length=25,
                    ),
                ),
                ("is_public", models.BooleanField(default=False)),
                ("scopes_text", models.TextField(null=True)),
                ("data", models.JSONField(null=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="FeedBack",
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
                ("message", models.TextField()),
                ("like", models.BooleanField(default=False)),
                ("dislike", models.BooleanField(default=False)),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedbacks",
                        to="agents.agent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="feedbacks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
