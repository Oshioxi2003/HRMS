# Generated by Django 5.1.6 on 2025-03-30 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='visibility',
            field=models.CharField(choices=[('Private', 'Riêng tư'), ('Department', 'Phòng ban'), ('Company', 'Công ty')], default='Private', max_length=20),
        ),
    ]
