# Generated by Django 5.0.4 on 2024-05-07 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0004_alter_bot_installed_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="thirdparty",
            field=models.CharField(
                choices=[
                    ("gmail", "Google Mail"),
                    ("google-calender", "Google Calender"),
                    ("google-document", "Google Document"),
                    ("google-drive", "Google Drive"),
                    ("google-sheet", "Google Sheet"),
                    ("google-form", "Google Form"),
                    ("salesforce", "Salesforce"),
                    ("slack", "Slack"),
                ],
                max_length=50,
                unique=True,
            ),
        ),
    ]