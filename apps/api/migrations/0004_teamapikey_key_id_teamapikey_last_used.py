# Generated by Django 5.1 on 2024-11-14 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_teamapikey_clear_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="teamapikey",
            name="key_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="teamapikey",
            name="last_used",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
