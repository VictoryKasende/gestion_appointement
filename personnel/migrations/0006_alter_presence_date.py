# Generated by Django 4.2.16 on 2024-10-03 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personnel', '0005_alter_presence_heure_arrivee_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='presence',
            name='date',
            field=models.DateField(),
        ),
    ]
