# Generated by Django 4.2.4 on 2023-11-26 12:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeeType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('is_required', models.BooleanField(default=True)),
                ('spot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.spot')),
            ],
        ),
        migrations.CreateModel(
            name='AudienceType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fee_type', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audience_type', to='api.feetype')),
            ],
        ),
    ]
