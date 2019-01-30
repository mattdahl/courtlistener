# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0083_generate_docket_number_core'),
    ]

    operations = [
        migrations.AddField(
            model_name='opinionscited',
            name='depth',
            field=models.IntegerField(default=1, help_text=b'The number of times the cited opinion was cited in the citing opinion', db_index=True),
        ),
    ]
