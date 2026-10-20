from django.db import migrations, models

import finanzas.models


def llenar_periodo(apps, schema_editor):
    """Los gastos que ya existían se quedan en el mes en que se capturaron."""
    Gasto = apps.get_model("finanzas", "GastoOperativo")
    for gasto in Gasto.objects.all():
        gasto.periodo = gasto.fecha.replace(day=1)
        gasto.save(update_fields=["periodo"])


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas", "0003_alter_gastooperativo_tipo"),
    ]

    operations = [
        migrations.AddField(
            model_name="gastooperativo",
            name="periodo",
            field=models.DateField(default=finanzas.models.mes_actual, verbose_name="Mes al que corresponde"),
        ),
        migrations.AlterModelOptions(
            name="gastooperativo",
            options={"ordering": ["-periodo", "-fecha"], "verbose_name": "Gasto operativo"},
        ),
        migrations.AddIndex(
            model_name="gastooperativo",
            index=models.Index(fields=["negocio", "periodo"], name="gasto_negocio_periodo_idx"),
        ),
        migrations.RunPython(llenar_periodo, migrations.RunPython.noop),
    ]
