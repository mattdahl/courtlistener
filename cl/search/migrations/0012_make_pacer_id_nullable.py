# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0011_tweak_pacer_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='docket',
            name='pacer_case_id',
            field=models.CharField(default='', help_text='The cased ID provided by PACER.', max_length=100, db_index=True, blank=True),
            preserve_default=False,
        ),
    ]
