import django.db.models.deletion
from django.db import migrations, models


def lotes_de_lo_que_ya_hay(apps, schema_editor):
    """Los productos que ya tenían piezas empiezan con un solo lote, al costo que tienen hoy."""
    Producto = apps.get_model("inventario", "Producto")
    Lote = apps.get_model("inventario", "LoteInventario")
    lotes = [
        Lote(
            negocio_id=p.negocio_id, producto=p, cantidad_inicial=p.cantidad_actual,
            cantidad_restante=p.cantidad_actual, costo_unitario=p.costo,
        )
        for p in Producto.objects.filter(cantidad_actual__gt=0).iterator()
    ]
    Lote.objects.bulk_create(lotes, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_negocio_preferencias_usuario_video_visto'),
        ('inventario', '0004_movimientoinventario'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimientoinventario',
            name='costo_unitario',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True),
        ),
        migrations.CreateModel(
            name='LoteInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('cantidad_inicial', models.DecimalField(decimal_places=3, max_digits=10)),
                ('cantidad_restante', models.DecimalField(decimal_places=3, max_digits=10)),
                ('costo_unitario', models.DecimalField(decimal_places=4, max_digits=12)),
                ('negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lotes_inventario', to='accounts.negocio')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lotes', to='inventario.producto')),
            ],
            options={
                'verbose_name': 'Lote de inventario',
                'verbose_name_plural': 'Lotes de inventario',
                'ordering': ['creado_en', 'id'],
                'indexes': [models.Index(fields=['producto', 'cantidad_restante'], name='lote_producto_restante_idx')],
            },
        ),
        migrations.RunPython(lotes_de_lo_que_ya_hay, migrations.RunPython.noop),
    ]
