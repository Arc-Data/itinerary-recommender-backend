# Generated by Django 4.2.4 on 2023-12-08 08:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_audiencetype_description_alter_audiencetype_price'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CustomFee',
        ),
    ]
