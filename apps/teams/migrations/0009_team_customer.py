# Generated by Django 5.1 on 2024-10-01 22:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0012_2_8"),
        ("teams", "0008_team_is_private"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="djstripe.customer",
            ),
        ),
    ]
