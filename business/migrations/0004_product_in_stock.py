# Generated by Django 5.0.4 on 2024-05-05 05:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0003_product_image2'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='in_stock',
            field=models.BooleanField(default=True),
        ),
    ]
