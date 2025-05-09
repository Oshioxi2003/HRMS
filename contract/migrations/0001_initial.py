# Generated by Django 5.1.6 on 2025-03-28 14:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('employee', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmploymentContract',
            fields=[
                ('contract_id', models.AutoField(primary_key=True, serialize=False)),
                ('contract_type', models.CharField(choices=[('Probation', 'Probation'), ('Fixed-term', 'Fixed-term'), ('Indefinite-term', 'Indefinite-term'), ('Seasonal', 'Seasonal')], max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('base_salary', models.DecimalField(decimal_places=2, max_digits=15)),
                ('allowance', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('attached_file', models.FileField(blank=True, null=True, upload_to='contract_documents/')),
                ('sign_date', models.DateField(blank=True, null=True)),
                ('signed_by', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Active', 'Active'), ('Expired', 'Expired'), ('Terminated', 'Terminated')], default='Active', max_length=20)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='employee.employee')),
            ],
        ),
    ]
