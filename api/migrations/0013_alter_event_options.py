# Generated by Django 4.2.4 on 2024-01-03 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_alter_driver_contact'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='event',
            options={'ordering': ['start_date']},
        ),
    ]
