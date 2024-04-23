# Generated by Django 5.0.4 on 2024-04-17 08:43

import hashid_field.field
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="State",
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
                ("is_used", models.BooleanField(default=False)),
                ("state", models.CharField(max_length=300)),
                (
                    "thirdparty",
                    models.CharField(
                        choices=[
                            ("google", "Google Workspace"),
                            ("salesforce", "Salesforce"),
                            ("slack", "Slack"),
                        ],
                        max_length=25,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]