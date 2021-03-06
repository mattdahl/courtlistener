# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('donate', '0002_donation_donor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donation',
            name='payment_provider',
            field=models.CharField(default=None, max_length=50, choices=[('dwolla', 'Dwolla'), ('paypal', 'PayPal'), ('cc', 'Credit Card'), ('check', 'Check'), ('bitcoin', 'Bitcoin')]),
        ),
    ]
