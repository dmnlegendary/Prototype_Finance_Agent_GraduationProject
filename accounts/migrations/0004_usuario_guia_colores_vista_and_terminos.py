from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_negocio_preferencias_usuario_video_visto'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='guia_colores_vista',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usuario',
            name='terminos_aceptados_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
