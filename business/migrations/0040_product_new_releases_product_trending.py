# Generated by Django 4.2.13 on 2024-06-21 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0039_order_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='new_releases',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='trending',
            field=models.BooleanField(default=False),
        ),
    ]
