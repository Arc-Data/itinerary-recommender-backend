# Generated by Django 4.2.4 on 2023-11-22 15:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_remove_accommodation_contact_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='description',
            field=models.CharField(default='No Description Provided.', max_length=1200),
        ),
    ]
