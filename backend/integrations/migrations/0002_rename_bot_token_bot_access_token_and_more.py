# Generated by Django 5.0.4 on 2024-04-25 00:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bot",
            old_name="bot_token",
            new_name="access_token",
        ),
        migrations.RenameField(
            model_name="bot",
            old_name="bot_token_expires_at",
            new_name="access_token_expires_in",
        ),
    ]
