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
            name='TrainingCourse',
            fields=[
                ('course_id', models.AutoField(primary_key=True, serialize=False)),
                ('course_name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=200, null=True)),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('organizer', models.CharField(blank=True, max_length=100, null=True)),
                ('supervisor', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('Preparing', 'Preparing'), ('In Progress', 'In Progress'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Preparing', max_length=20)),
                ('max_participants', models.PositiveIntegerField(blank=True, help_text='Maximum number of participants allowed', null=True)),
                ('prerequisites', models.TextField(blank=True, help_text='Prerequisites for attending this course', null=True)),
                ('materials', models.TextField(blank=True, help_text='Course materials and resources', null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='training_images/')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(blank=True, help_text='If set, this course is specific to this department', null=True, on_delete=django.db.models.deletion.SET_NULL, to='employee.department')),
            ],
        ),
        migrations.CreateModel(
            name='TrainingParticipation',
            fields=[
                ('participation_id', models.AutoField(primary_key=True, serialize=False)),
                ('registration_date', models.DateField()),
                ('expected_completion_date', models.DateField(blank=True, null=True)),
                ('actual_completion_date', models.DateField(blank=True, null=True)),
                ('approval_status', models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Approved', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('achievement', models.CharField(blank=True, max_length=100, null=True)),
                ('feedback', models.TextField(blank=True, null=True)),
                ('certificate', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('Registered', 'Registered'), ('Participating', 'Participating'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Registered', max_length=20)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='training.trainingcourse')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='employee.employee')),
            ],
            options={
                'unique_together': {('employee', 'course')},
            },
        ),
    ]
