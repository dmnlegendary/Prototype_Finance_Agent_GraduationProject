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


@dataclass
class CandidateResult:
    name: str
    forecast: float
    mae: float


def _linear_regression(values: np.ndarray) -> float:
    x = np.arange(len(values), dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x, values)
    return max(0.0, float(model.predict([[len(values)]])[0]))


def _arima(values: np.ndarray) -> float:
    from statsmodels.tsa.arima.model import ARIMA

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(values, order=(1, 1, 0), enforce_stationarity=False)
        return max(0.0, float(model.fit().forecast(steps=1)[0]))


def _holt_winters(values: np.ndarray) -> float:
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
    return max(0.0, float(values[-1]))


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _score_candidate(values: np.ndarray, name: str, predictor: Callable[[np.ndarray], float]) -> CandidateResult | None:
    if len(values) < MINIMUM_WEEKS:
        return None

    holdout_size = min(4, max(2, len(values) // 4))
    train = values[:-holdout_size]
    actual = values[-holdout_size:]
    predictions = []

    for index in range(holdout_size):
        try:
            predictions.append(predictor(values[: len(train) + index]))
        except (ValueError, np.linalg.LinAlgError):
            return None

    try:
        forecast = predictor(values)
    except (ValueError, np.linalg.LinAlgError):
        return None
    return CandidateResult(name, forecast, _mae(actual, np.array(predictions)))


def _weekly_series(negocio) -> tuple[list[date], np.ndarray]:
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
    while current <= last_week:
        weeks.append(current)
        values.append(by_week.get(current, 0.0))
        current += timedelta(days=7)

    first_sale_date = timezone.localtime(bounds["first"]).date()
    last_sale_date = timezone.localtime(bounds["last"]).date()
    if weeks and first_sale_date > weeks[0]:
        weeks = weeks[1:]
        values = values[1:]
    if weeks and last_sale_date < weeks[-1] + timedelta(days=6):
        weeks = weeks[:-1]
        values = values[:-1]

    return weeks, np.array(values, dtype=float)


def forecast_sales(negocio) -> dict:
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
        selected = CandidateResult("Línea base (última semana)", _naive(values), 0.0)
        confidence = 35
        message = f"Se requieren al menos {MINIMUM_WEEKS} semanas para comparar modelos."
    else:
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