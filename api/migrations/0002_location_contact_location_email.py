# Generated by Django 4.2.4 on 2023-11-20 17:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='contact',
            field=models.CharField(blank=True, default='', max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='location',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254, null=True),
        ),
    ]
