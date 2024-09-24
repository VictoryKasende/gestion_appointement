# Generated by Django 4.2.16 on 2024-09-20 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='date_entree',
            field=models.DateField(blank=True, null=True, verbose_name="Date d'entrée"),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='departement',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Département'),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='poste',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Poste'),
        ),
        migrations.AddField(
            model_name='utilisateur',
            name='rfid_number',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True, verbose_name='Numéro RFID'),
        ),
    ]
