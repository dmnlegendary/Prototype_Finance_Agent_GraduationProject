-- Consultas útiles de marIA (PostgreSQL).
-- Cambia el 1 de "negocio_id = 1" por el id de tu tienda
-- (lo ves con: SELECT id, nombre_tienda FROM accounts_negocio;)


-- 1. Ventas por día de los últimos 30 días
SELECT creado_en::date AS dia,
       COUNT(*)        AS tickets,
       SUM(total)      AS vendido
FROM ventas_venta
WHERE negocio_id = 1
  AND estado = 'COBRADA'
  AND creado_en >= NOW() - INTERVAL '30 days'
GROUP BY dia
ORDER BY dia;


-- 2. Los 10 productos más vendidos (por piezas)
SELECT p.nombre,
       SUM(i.cantidad)                      AS piezas,
       SUM(i.cantidad * i.precio_unitario)  AS vendido
FROM ventas_itemventa i
JOIN ventas_venta v    ON v.id = i.venta_id
JOIN inventario_producto p ON p.id = i.producto_id
WHERE v.negocio_id = 1 AND v.estado = 'COBRADA'
GROUP BY p.nombre
ORDER BY piezas DESC
LIMIT 10;


-- 3. Semáforo de reabastecimiento
--    rojo: llegó al mínimo | naranja: queda un cuarto del ideal | amarillo: va a la mitad
--    (si el stock ideal está en 0 se usa 4 veces el mínimo)
SELECT nombre, cantidad_actual, cantidad_minima, ideal,
       CASE
         WHEN cantidad_actual <= cantidad_minima                      THEN 'rojo'
         WHEN cantidad_actual <= GREATEST(ideal / 4, cantidad_minima) THEN 'naranja'
         WHEN cantidad_actual <= GREATEST(ideal / 2, cantidad_minima) THEN 'amarillo'
         ELSE 'ok'
       END AS color
FROM (
    SELECT nombre, cantidad_actual, cantidad_minima,
           CASE WHEN stock_ideal > cantidad_minima THEN stock_ideal ELSE cantidad_minima * 4 END AS ideal
    FROM inventario_producto
    WHERE negocio_id = 1 AND activo
) AS productos
ORDER BY cantidad_actual - cantidad_minima;


-- 4. Gastos por mes y tipo
SELECT date_trunc('month', fecha)::date AS mes,
       tipo,
       SUM(monto) AS total
FROM finanzas_gastooperativo
WHERE negocio_id = 1
GROUP BY mes, tipo
ORDER BY mes DESC, tipo;


-- 5. Ganancia bruta por mes (lo vendido menos lo que costó la mercancía)
SELECT date_trunc('month', v.creado_en)::date AS mes,
       SUM(i.cantidad * i.precio_unitario)    AS ingresos,
       SUM(i.cantidad * p.costo)              AS costo_de_ventas,
       SUM(i.cantidad * (i.precio_unitario - p.costo)) AS ganancia_bruta
FROM ventas_itemventa i
JOIN ventas_venta v        ON v.id = i.venta_id
JOIN inventario_producto p ON p.id = i.producto_id
WHERE v.negocio_id = 1 AND v.estado = 'COBRADA'
GROUP BY mes
ORDER BY mes DESC;


-- 6. Productos que no se han vendido en los últimos 60 días (baja rotación)
SELECT p.nombre, p.cantidad_actual
FROM inventario_producto p
WHERE p.negocio_id = 1 AND p.activo
  AND NOT EXISTS (
      SELECT 1
      FROM ventas_itemventa i
      JOIN ventas_venta v ON v.id = i.venta_id
      WHERE i.producto_id = p.id
        AND v.estado = 'COBRADA'
        AND v.creado_en >= NOW() - INTERVAL '60 days'
  )
ORDER BY p.cantidad_actual DESC;
