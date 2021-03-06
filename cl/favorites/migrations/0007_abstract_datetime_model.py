# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-12-23 14:43
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('favorites', '0006_ditch_generic_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usertag',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, db_index=True, help_text='The moment when the item was created.'),
        ),
        migrations.AlterField(
            model_name='usertag',
            name='date_modified',
            field=models.DateTimeField(auto_now=True, db_index=True, help_text='The last moment when the item was modified. A value in year 1750 indicates the value is unknown'),
        ),
    ]
