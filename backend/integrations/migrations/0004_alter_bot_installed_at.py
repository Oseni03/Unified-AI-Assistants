# Generated by Django 5.0.4 on 2024-04-30 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0003_remove_integration_scopes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bot",
            name="installed_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]