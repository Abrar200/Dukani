# Generated by Django 4.2.13 on 2024-05-15 23:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0012_alter_message_options_rename_body_message_content_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='state',
            field=models.CharField(choices=[('ACT', 'Australian Capital Territory'), ('NSW', 'New South Wales'), ('NT', 'Northern Territory'), ('QLD', 'Queensland'), ('SA', 'South Australia'), ('TAS', 'Tasmania'), ('VIC', 'Victoria'), ('WA', 'Western Australia')], max_length=3, null=True),
        ),
    ]
