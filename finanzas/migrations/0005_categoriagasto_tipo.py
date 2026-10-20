from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finanzas', '0004_gastooperativo_periodo'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoriagasto',
            name='tipo',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
    ]
