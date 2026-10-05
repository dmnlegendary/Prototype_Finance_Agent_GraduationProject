"""Pronostico semanal de unidades vendidas para un negocio.

El flujo toma las ventas cobradas, crea una serie cronologica de unidades por
semana completa, compara varios pronosticadores con validacion temporal y
devuelve una estimacion para la semana siguiente. No pronostica ingresos ni
separa los resultados por producto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable
import warnings

import numpy as np
from django.db.models import Max, Min, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from sklearn.linear_model import LinearRegression
from ventas.models import Venta


MINIMUM_WEEKS = 8
"""Numero minimo de observaciones semanales para comparar modelos."""


@dataclass
class CandidateResult:
    """Resultado de un modelo que pudo evaluarse.

    Attributes:
        name: Etiqueta legible del modelo.
        forecast: Pronostico de un paso calculado con toda la serie disponible.
        mae: Error absoluto medio medido en las semanas reservadas para
            validacion. Se expresa en las mismas unidades que las ventas.
    """

    name: str
    forecast: float
    mae: float


def _linear_regression(values: np.ndarray) -> float:
    """Extrapola una tendencia lineal para una semana despues de `values`.

    Cada observacion recibe un indice consecutivo (0, 1, ..., n-1). El modelo
    se ajusta con esos indices y predice en n, que representa el siguiente
    periodo. No modela estacionalidad. El resultado se convierte a `float` y
    se limita a cero para evitar pronosticos negativos.
    """
    x = np.arange(len(values), dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x, values)
    return max(0.0, float(model.predict([[len(values)]])[0]))


def _arima(values: np.ndarray) -> float:
    """Ajusta ARIMA(1,1,0) y devuelve el pronostico de un periodo.

    `enforce_stationarity=False` permite ajustar el modelo sin exigir esa
    restriccion de estacionariedad. Las advertencias de statsmodels se
    silencian durante el ajuste; los errores no se ocultan aqui. El llamador
    puede descartar el candidato si el ajuste lanza ValueError o
    `numpy.linalg.LinAlgError`.
    """
    from statsmodels.tsa.arima.model import ARIMA

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(values, order=(1, 1, 0), enforce_stationarity=False)
        return max(0.0, float(model.fit().forecast(steps=1)[0]))


def _holt_winters(values: np.ndarray) -> float:
    """Ajusta suavizado exponencial con tendencia y pronostica un periodo.

    Usa tendencia aditiva. Con 12 observaciones o mas agrega estacionalidad
    aditiva de periodo 4; con menos observaciones no configura estacionalidad.
    Los parametros se inicializan mediante estimacion y statsmodels los
    optimiza durante el ajuste.
    """
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    model = ExponentialSmoothing(
        values,
        trend="add",
        seasonal="add" if len(values) >= 12 else None,
        seasonal_periods=4 if len(values) >= 12 else None,
        initialization_method="estimated",
    )
    return max(0.0, float(model.fit(optimized=True).forecast(1)[0]))


def _naive(values: np.ndarray) -> float:
    """Usa las unidades de la ultima semana como pronostico siguiente.

    Es una linea base de respaldo, no uno de los modelos que se comparan por
    MAE. Requiere una serie no vacia y evita devolver valores negativos.
    """
    return max(0.0, float(values[-1]))


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calcula el promedio de `abs(valor_real - prediccion)`.

    Un MAE menor significa que, en promedio, las predicciones quedaron mas
    cerca de los valores observados. El resultado conserva las unidades de la
    serie (unidades vendidas por semana).
    """
    return float(np.mean(np.abs(actual - predicted)))


def _score_candidate(values: np.ndarray, name: str, predictor: Callable[[np.ndarray], float]) -> CandidateResult | None:
    """Valida un pronosticador en el tramo final y calcula su siguiente valor.

    Devuelve `None` si la serie tiene menos de `MINIMUM_WEEKS` o si una de las
    predicciones/ajustes falla con ValueError o `numpy.linalg.LinAlgError`.
    Para las demas series reserva entre 2 y 4 observaciones finales: el cuarto
    de la serie, limitado a ese intervalo. Las semanas reservadas son el
    conjunto de validacion; el resto inicia el entrenamiento.

    La validacion avanza una semana a la vez. Para predecir la primera semana
    reservada se usa solo el entrenamiento inicial; para la siguiente se
    incorpora al prefijo el valor real de la semana reservada anterior. Asi,
    cada pronostico usa unicamente datos que ya se conocerian en ese momento.
    El MAE compara las predicciones con los valores reales reservados.

    Finalmente, el predictor se vuelve a ejecutar con toda la serie para
    calcular el pronostico futuro que se guarda en `CandidateResult`. El MAE
    mide la validacion, no el ajuste sobre esos datos completos.
    """
    if len(values) < MINIMUM_WEEKS:
        return None

    # Reserva de 2 a 4 semanas: n // 4, limitado a ese intervalo.
    holdout_size = min(4, max(2, len(values) // 4))
    train = values[:-holdout_size]
    actual = values[-holdout_size:]
    predictions = []

    for index in range(holdout_size):
        try:
            # El prefijo crece con cada paso e incorpora semanas reales ya observadas.
            predictions.append(predictor(values[: len(train) + index]))
        except (ValueError, np.linalg.LinAlgError):
            return None

    try:
        forecast = predictor(values)
    except (ValueError, np.linalg.LinAlgError):
        return None
    return CandidateResult(name, forecast, _mae(actual, np.array(predictions)))


def _weekly_series(negocio) -> tuple[list[date], np.ndarray]:
    """Construye las fechas y unidades semanales completas de un negocio.

    Solo incluye ventas con estado `COBRADA` del negocio recibido. Agrupa por
    semana de creacion de la venta y suma las cantidades de sus articulos; por
    tanto, la serie representa unidades, no montos monetarios.

    Entre la primera y la ultima semana encontrada, completa con cero las
    semanas sin ventas para que los modelos reciban una secuencia continua.
    Despues descarta la semana inicial si la primera venta ocurrio despues de
    su primer dia, y la semana final si la ultima venta ocurrio antes de su
    ultimo dia. Devuelve las fechas de inicio de las semanas conservadas y un
    arreglo NumPy de cantidades alineado con esas fechas.

    Si no existen ventas cobradas o no hay filas agrupadas, devuelve una lista
    y un arreglo vacios. La llamada a `timezone.localtime` usa la zona horaria
    activa de Django para revisar las fechas limite de las semanas.
    """
    sales = Venta.objects.filter(
        negocio=negocio,
        estado=Venta.Estado.COBRADA,
    )
    bounds = sales.aggregate(first=Min("creado_en"), last=Max("creado_en"))
    if bounds["first"] is None:
        return [], np.array([], dtype=float)

    rows = list(
        sales
        .annotate(semana=TruncWeek("creado_en"))
        .values("semana")
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("semana")
    )
    if not rows:
        return [], np.array([], dtype=float)

    first_week = rows[0]["semana"].date()
    last_week = rows[-1]["semana"].date()
    by_week = {row["semana"].date(): float(row["unidades"] or 0) for row in rows}
    weeks = []
    values = []
    current = first_week
    # Crear tambien las semanas sin ventas intermedias, con cero unidades.
    while current <= last_week:
        weeks.append(current)
        values.append(by_week.get(current, 0.0))
        current += timedelta(days=7)

    first_sale_date = timezone.localtime(bounds["first"]).date()
    last_sale_date = timezone.localtime(bounds["last"]).date()
    # No entrenar con semanas parciales en los extremos del historial.
    if weeks and first_sale_date > weeks[0]:
        weeks = weeks[1:]
        values = values[1:]
    if weeks and last_sale_date < weeks[-1] + timedelta(days=6):
        weeks = weeks[:-1]
        values = values[:-1]

    return weeks, np.array(values, dtype=float)


def forecast_sales(negocio) -> dict:
    """Genera un pronostico semanal de unidades y los datos para presentarlo.

    Primero obtiene la serie de semanas completas. Sin observaciones devuelve
    `ok=False` y un mensaje, sin intentar ajustar modelos. Con datos, evalua
    regresion lineal, ARIMA y Holt-Winters mediante `_score_candidate`; los
    candidatos que no alcanzan el minimo o cuyo ajuste falla se omiten.

    Entre los candidatos validos selecciona el menor MAE. Si no queda ninguno,
    usa la ultima semana como linea base, asigna MAE 0 y confianza 35; ese MAE
    no proviene de una validacion. En esa rama, el mensaje indica que se
    requieren al menos `MINIMUM_WEEKS`, aunque tambien puede ocurrir que los
    modelos no se hayan podido ajustar.

    La confianza de la rama con modelo es un indicador heuristico: parte de
    `100 - MAE / max(promedio_semanal, 1) * 100` y se limita al intervalo
    35-95. No es una probabilidad estadistica. `next_week` es la fecha de
    inicio de la semana posterior a la ultima semana completa.

    Returns:
        Diccionario serializable como JSON. Si `ok` es verdadero, incluye el
        modelo elegido, unidades pronosticadas, MAE, confianza, fecha de la
        siguiente semana, cantidad de semanas, mensaje y candidatos ordenados
        por MAE. La lista `candidates` queda vacia cuando se usa la linea base.
    """
    weeks, values = _weekly_series(negocio)
    if not values.size:
        return {
            "ok": False,
            "message": "No hay semanas completas de ventas cobradas para entrenar un pronóstico.",
        }

    candidates = [
        _score_candidate(values, "Regresión lineal", _linear_regression),
        _score_candidate(values, "ARIMA(1,1,0)", _arima),
        _score_candidate(values, "Holt-Winters", _holt_winters),
    ]
    candidates = [candidate for candidate in candidates if candidate is not None]
    if not candidates:
        # Respaldo cuando hay pocas semanas o ningun modelo pudo validarse.
        selected = CandidateResult("Línea base (última semana)", _naive(values), 0.0)
        confidence = 35
        message = f"Se requieren al menos {MINIMUM_WEEKS} semanas para comparar modelos."
    else:
        # El menor MAE en la validacion temporal decide que modelo se reporta.
        selected = min(candidates, key=lambda candidate: candidate.mae)
        confidence = max(35, min(95, round(100 - selected.mae / max(values.mean(), 1) * 100)))
        message = "Modelo elegido por menor error absoluto medio en validación temporal."

    return {
        "ok": True,
        "model": selected.name,
        "forecast_units": round(selected.forecast, 2),
        "mae": round(selected.mae, 2),
        "confidence": confidence,
        "next_week": (weeks[-1] + timedelta(days=7)).isoformat(),
        "weeks": len(values),
        "message": message,
        "candidates": [
            {"model": candidate.name, "mae": round(candidate.mae, 2)}
            for candidate in sorted(candidates, key=lambda candidate: candidate.mae)
        ],
    }