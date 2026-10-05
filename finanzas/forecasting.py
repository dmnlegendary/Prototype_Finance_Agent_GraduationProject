"""Pronostico semanal de unidades vendidas para los productos mas populares.

El flujo identifica los productos con mayor volumen de ventas cobradas,
construye una serie semanal por producto, compara varios pronosticadores con
validacion temporal y devuelve estimaciones individuales. No pronostica
ingresos.
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
from ventas.models import ItemVenta, Venta


MINIMUM_WEEKS = 8
"""Numero minimo de observaciones semanales para comparar modelos."""

POPULAR_PRODUCTS_LIMIT = 10
"""Numero maximo de productos que se incluyen en el pronostico."""

_ARIMA_ORDERS = (
    ((0, 1, 0), None),
    ((0, 1, 0), "t"),
    ((1, 1, 0), None),
    ((0, 1, 1), None),
    ((1, 1, 1), None),
    ((1, 0, 0), None),
    ((0, 0, 1), None),
)


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
    """Elige un orden ARIMA pequeno por AIC y pronostica un periodo.

    Compara combinaciones simples de ARIMA estacionario y diferenciado, tanto
    sin tendencia como con deriva. Solo considera ajustes convergentes con AIC
    y pronostico finitos. Para una serie constante devuelve su ultimo valor
    directamente; si ningun ajuste sirve, el llamador puede descartar el
    candidato cuando recibe ValueError.
    """
    if not values.size:
        raise ValueError("ARIMA requiere al menos una observacion.")
    if np.all(values == values[0]):
        return max(0.0, float(values[-1]))

    from statsmodels.tsa.arima.model import ARIMA

    best_aic = float("inf")
    best_forecast = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for order, trend in _ARIMA_ORDERS:
            try:
                result = ARIMA(values, order=order, trend=trend).fit()
                aic = float(result.aic)
                if not result.mle_retvals.get("converged", True) or not np.isfinite(aic):
                    continue

                forecast = float(result.forecast(steps=1)[0])
                if np.isfinite(forecast) and aic < best_aic:
                    best_aic = aic
                    best_forecast = forecast
            except (ValueError, np.linalg.LinAlgError):
                continue

    if best_forecast is None:
        raise ValueError("No se pudo ajustar un orden ARIMA convergente.")
    return max(0.0, best_forecast)


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


def _top_products(negocio) -> list[dict]:
    """Devuelve los productos del negocio con mayor volumen historico vendido."""
    return list(
        ItemVenta.objects.filter(
            venta__negocio=negocio,
            venta__estado=Venta.Estado.COBRADA,
        )
        .values("producto_id", "producto__nombre", "producto__icono")
        .annotate(unidades_vendidas=Sum("cantidad"))
        .order_by("-unidades_vendidas", "producto__nombre")[:POPULAR_PRODUCTS_LIMIT]
    )


def _weekly_series(negocio, producto_id: int) -> tuple[list[date], np.ndarray]:
    """Construye las unidades semanales completas de un producto del negocio.

    El rango de semanas se determina usando todas las ventas cobradas del
    negocio para que cada producto comparta el mismo periodo de referencia.
    Los articulos se filtran por `producto_id` y sus cantidades se agrupan por
    semana; las semanas sin ventas del producto se completan con cero.

    Se descartan las semanas inicial y final si son parciales respecto al
    historial del negocio. Devuelve fechas alineadas con un arreglo NumPy de
    unidades; si no hay semanas completas, ambos resultados estan vacios.

    La llamada a `timezone.localtime` usa la zona horaria activa de Django para
    revisar las fechas limite de las semanas.
    """
    sales = Venta.objects.filter(
        negocio=negocio,
        estado=Venta.Estado.COBRADA,
    )
    bounds = sales.aggregate(first=Min("creado_en"), last=Max("creado_en"))
    if bounds["first"] is None:
        return [], np.array([], dtype=float)

    rows = list(
        sales.filter(items__producto_id=producto_id)
        .annotate(semana=TruncWeek("creado_en"))
        .values("semana")
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("semana")
    )
    first_sale_date = timezone.localtime(bounds["first"]).date()
    last_sale_date = timezone.localtime(bounds["last"]).date()
    first_week = first_sale_date - timedelta(days=first_sale_date.weekday())
    last_week = last_sale_date - timedelta(days=last_sale_date.weekday())
    by_week = {row["semana"].date(): float(row["unidades"] or 0) for row in rows}
    weeks = []
    values = []
    current = first_week
    # Crear tambien las semanas sin ventas intermedias, con cero unidades.
    while current <= last_week:
        weeks.append(current)
        values.append(by_week.get(current, 0.0))
        current += timedelta(days=7)

    # No entrenar con semanas parciales en los extremos del historial.
    if weeks and first_sale_date > weeks[0]:
        weeks = weeks[1:]
        values = values[1:]
    if weeks and last_sale_date < weeks[-1] + timedelta(days=6):
        weeks = weeks[:-1]
        values = values[:-1]

    return weeks, np.array(values, dtype=float)


def _forecast_product(product: dict, values: np.ndarray) -> dict:
    """Compara modelos para un producto y devuelve su pronostico individual."""
    candidates = [
        _score_candidate(values, "Regresión lineal", _linear_regression),
        _score_candidate(values, "ARIMA (orden por AIC)", _arima),
        _score_candidate(values, "Holt-Winters", _holt_winters),
    ]
    candidates = [candidate for candidate in candidates if candidate is not None]
    if not candidates:
        selected = CandidateResult("Línea base (última semana)", _naive(values), 0.0)
        confidence = 35
        message = f"Se requieren al menos {MINIMUM_WEEKS} semanas para comparar modelos."
    else:
        selected = min(candidates, key=lambda candidate: candidate.mae)
        confidence = max(35, min(95, round(100 - selected.mae / max(values.mean(), 1) * 100)))
        message = "Modelo elegido por menor error absoluto medio en validación temporal."

    return {
        "product_id": product["producto_id"],
        "name": product["producto__nombre"],
        "icon": product["producto__icono"],
        "model": selected.name,
        "forecast_units": round(selected.forecast, 2),
        "mae": round(selected.mae, 2),
        "confidence": confidence,
        "weeks": len(values),
        "message": message,
        "candidates": [
            {"model": candidate.name, "mae": round(candidate.mae, 2)}
            for candidate in sorted(candidates, key=lambda candidate: candidate.mae)
        ],
    }


def forecast_sales(negocio) -> dict:
    """Genera pronosticos semanales individuales para los 10 mas vendidos.

    La popularidad se mide por unidades en ventas cobradas. Para cada producto
    se evalua por separado regresion lineal, ARIMA (orden elegido por AIC) y
    Holt-Winters, y se elige el de menor MAE en validacion temporal. Si no hay
    suficientes semanas o los modelos no se ajustan, se usa la ultima semana
    como linea base. La confianza reportada es un indicador heuristico, no una
    probabilidad estadistica.

    Returns:
        Diccionario serializable como JSON con la fecha comun de pronostico y
        hasta diez productos con sus estimaciones y comparaciones de modelos.
    """
    products = _top_products(negocio)
    if not products:
        return {
            "ok": False,
            "message": "No hay productos con ventas cobradas para pronosticar.",
        }

    forecasts = []
    last_complete_week = None
    for product in products:
        weeks, values = _weekly_series(negocio, product["producto_id"])
        if values.size:
            last_complete_week = weeks[-1]
            forecasts.append(_forecast_product(product, values))

    if not forecasts or last_complete_week is None:
        return {
            "ok": False,
            "message": "No hay semanas completas de ventas cobradas para pronosticar.",
        }

    return {
        "ok": True,
        "next_week": (last_complete_week + timedelta(days=7)).isoformat(),
        "products": forecasts,
    }