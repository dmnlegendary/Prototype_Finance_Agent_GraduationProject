from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas", "0005_categoriagasto_tipo"),
    ]

    operations = [
        migrations.AddField(
            model_name="gastooperativo",
            name="periodicidad",
            field=models.CharField(
                choices=[
                    ("UNA_VEZ", "Una sola vez"),
                    ("DIARIA", "Diaria"),
                    ("SEMANAL", "Semanal"),
                    ("MENSUAL", "Mensual"),
                    ("ANUAL", "Anual"),
                ],
                default="UNA_VEZ",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="gastooperativo",
            name="fecha_inicio",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="gastooperativo",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        models.Q(("fecha_inicio__isnull", True), ("periodicidad", "UNA_VEZ")),
                        models.Q(
                            ("fecha_inicio__isnull", False),
                            ("periodicidad__in", ["DIARIA", "SEMANAL", "MENSUAL", "ANUAL"]),
                            ("tipo", "FIJO"),
                        ),
                        _connector="OR",
                    )
                ),
                name="gasto_periodicidad_coherente",
            ),
        ),
    ]
