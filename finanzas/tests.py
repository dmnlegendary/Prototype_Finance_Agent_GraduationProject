import numpy as np
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from unittest.mock import patch

from accounts.models import Negocio
from finanzas.forecasting import (
    _arima,
    _forecast_product,
    _top_products,
    _weekly_series,
    forecast_sales,
)
from inventario.models import Producto
from ventas.models import ItemVenta, Venta


class ArimaForecastTests(SimpleTestCase):
    def test_constant_series_returns_last_value_without_fitting(self):
        values = np.full(8, 12.0)

        with patch("statsmodels.tsa.arima.model.ARIMA") as arima:
            forecast = _arima(values)

        self.assertEqual(forecast, 12.0)
        arima.assert_not_called()

    def test_selects_lowest_aic_among_converged_orders(self):
        fits = {
            ((0, 1, 0), None): (20.0, 8.0, True),
            ((0, 1, 0), "t"): (15.0, 11.0, False),
            ((1, 1, 0), None): (10.0, 14.0, True),
            ((0, 1, 1), None): (12.0, 13.0, True),
            ((1, 1, 1), None): (13.0, 12.0, True),
            ((1, 0, 0), None): (14.0, 11.0, True),
            ((0, 0, 1), None): (16.0, 10.0, True),
        }

        class FakeResult:
            def __init__(self, aic, forecast, converged):
                self.aic = aic
                self.mle_retvals = {"converged": converged}
                self.forecast_value = forecast

            def forecast(self, steps):
                if steps != 1:
                    raise AssertionError("ARIMA debe pronosticar un periodo.")
                return [self.forecast_value]

        class FakeARIMA:
            def __init__(self, values, order, trend=None):
                if not values.size:
                    raise AssertionError("La prueba requiere una serie no vacia.")
                self.order_and_trend = (order, trend)

            def fit(self):
                return FakeResult(*fits[self.order_and_trend])

        with patch("statsmodels.tsa.arima.model.ARIMA", FakeARIMA):
            forecast = _arima(np.array([2, 5, 3, 7, 4, 9, 6, 11], dtype=float))

        self.assertEqual(forecast, 14.0)

    def test_empty_series_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, "al menos una observacion"):
            _arima(np.array([], dtype=float))


class ProductForecastTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="pronostico")
        self.business = Negocio.objects.create(usuario=user, nombre_tienda="Tienda de prueba")

    def create_product(self, name):
        return Producto.objects.create(
            negocio=self.business,
            nombre=name,
            costo=10,
            precio_venta=15,
        )

    def create_sale(self, folio, date):
        sale = Venta.objects.create(
            negocio=self.business,
            folio=folio,
            estado=Venta.Estado.COBRADA,
        )
        created_at = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        Venta.objects.filter(pk=sale.pk).update(creado_en=created_at)
        return sale

    def test_top_products_are_ranked_by_units_sold_and_limited_to_ten(self):
        products = [self.create_product(f"Producto {index:02}") for index in range(11)]
        sale = self.create_sale(1, datetime(2024, 1, 1).date())
        for index, product in enumerate(products):
            ItemVenta.objects.create(
                venta=sale,
                producto=product,
                cantidad=index + 1,
                precio_unitario=product.precio_venta,
            )

        ranked = _top_products(self.business)

        self.assertEqual(len(ranked), 10)
        self.assertEqual(ranked[0]["producto_id"], products[-1].id)
        self.assertNotIn(products[0].id, [product["producto_id"] for product in ranked])

    def test_product_series_uses_full_business_weeks_and_zero_fills(self):
        cola = self.create_product("Cola")
        refresco = self.create_product("Refresco")
        start = datetime(2024, 1, 1).date()
        for index in range(8):
            sale = self.create_sale(index + 1, start + timedelta(weeks=index))
            ItemVenta.objects.create(
                venta=sale,
                producto=cola,
                cantidad=index + 1,
                precio_unitario=cola.precio_venta,
            )
            if index == 2:
                ItemVenta.objects.create(
                    venta=sale,
                    producto=refresco,
                    cantidad=4,
                    precio_unitario=refresco.precio_venta,
                )
        last_sale = Venta.objects.get(folio=8)
        Venta.objects.filter(pk=last_sale.pk).update(
            creado_en=timezone.make_aware(datetime.combine(start + timedelta(weeks=8) - timedelta(days=1), datetime.min.time()))
        )

        weeks, values = _weekly_series(self.business, refresco.id)

        self.assertEqual(len(weeks), 8)
        np.testing.assert_array_equal(values, [0, 0, 4, 0, 0, 0, 0, 0])

    def test_product_fallback_includes_product_specific_forecast(self):
        product = {
            "producto_id": 23,
            "producto__nombre": "Cola",
            "producto__icono": "🥤",
        }

        forecast = _forecast_product(product, np.array([2, 0, 3], dtype=float))

        self.assertEqual(forecast["product_id"], 23)
        self.assertEqual(forecast["name"], "Cola")
        self.assertEqual(forecast["forecast_units"], 3.0)
        self.assertEqual(forecast["model"], "Línea base (última semana)")

    def test_forecast_sales_returns_one_forecast_per_top_product(self):
        cola = self.create_product("Cola")
        pepsi = self.create_product("Pepsi")
        start = datetime(2024, 1, 1).date()
        for index in range(8):
            sale = self.create_sale(index + 1, start + timedelta(weeks=index))
            for product, quantity in ((cola, 3), (pepsi, 5)):
                ItemVenta.objects.create(
                    venta=sale,
                    producto=product,
                    cantidad=quantity,
                    precio_unitario=product.precio_venta,
                )
        last_sale = Venta.objects.get(folio=8)
        Venta.objects.filter(pk=last_sale.pk).update(
            creado_en=timezone.make_aware(
                datetime.combine(start + timedelta(weeks=8) - timedelta(days=1), datetime.min.time())
            )
        )

        with patch(
            "finanzas.forecasting._forecast_product",
            side_effect=lambda product, values: {
                "product_id": product["producto_id"],
                "forecast_units": float(values[-1]),
            },
        ):
            result = forecast_sales(self.business)

        self.assertTrue(result["ok"])
        self.assertEqual(result["next_week"], "2024-02-26")
        self.assertEqual(
            [product["product_id"] for product in result["products"]],
            [pepsi.id, cola.id],
        )
