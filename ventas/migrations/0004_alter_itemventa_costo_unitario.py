from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0003_itemventa_costo_unitario_venta_carrito_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemventa',
            name='costo_unitario',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12),
        ),
    ]
