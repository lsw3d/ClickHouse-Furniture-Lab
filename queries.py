"""Десять запросов из ЛР5, каждый оформлен отдельной функцией."""

from datetime import date


def orders_in_period(client, db, start=date(2026, 2, 1), end=date(2026, 4, 1)):
    """Заказы за февраль и март 2026 года."""
    return client.query(
        f"""SELECT order_id, customer_id, order_date, status
FROM {db}.orders
WHERE order_date >= {{start:Date}}
  AND order_date < {{end:Date}}
ORDER BY order_date, order_id""", parameters={"start": start, "end": end}
    )


def order_details(client, db, order_id=101):
    """Состав заказа № 101."""
    return client.query(
        f"""SELECT
    o.order_id,
    c.last_name AS customer,
    p.name AS product,
    a.last_name AS assembler,
    oi.quantity,
    oi.quantity * oi.unit_price AS line_total
FROM {db}.orders AS o
INNER JOIN {db}.customers AS c
    ON o.customer_id = c.customer_id
INNER JOIN {db}.order_items AS oi
    ON o.order_id = oi.order_id
INNER JOIN {db}.products AS p
    ON oi.product_id = p.product_id
INNER JOIN {db}.assemblers AS a
    ON oi.assembler_id = a.assembler_id
WHERE o.order_id = {{order_id:UInt32}}
ORDER BY oi.item_id""", parameters={"order_id": order_id}
    )


def order_totals(client, db):
    """Стоимость каждого заказа."""
    return client.query(
        f"""SELECT
    o.order_id,
    c.last_name AS customer,
    sum(oi.quantity * oi.unit_price) AS order_total
FROM {db}.orders AS o
INNER JOIN {db}.customers AS c
    ON o.customer_id = c.customer_id
INNER JOIN {db}.order_items AS oi
    ON o.order_id = oi.order_id
GROUP BY o.order_id, c.last_name
ORDER BY o.order_id"""
    )


def monthly_revenue(client, db):
    """Выручка по месяцам завершения заказов."""
    return client.query(
        f"""SELECT
    toStartOfMonth(o.completed_date) AS month,
    uniqExact(o.order_id) AS completed_orders,
    sum(oi.quantity * oi.unit_price) AS revenue
FROM {db}.orders AS o
INNER JOIN {db}.order_items AS oi
    ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY month
ORDER BY month"""
    )


def category_revenue(client, db):
    """Выручка по категориям мебели."""
    return client.query(
        f"""SELECT
    p.category,
    sum(oi.quantity) AS units_sold,
    sum(oi.quantity * oi.unit_price) AS revenue
FROM {db}.order_items AS oi
INNER JOIN {db}.orders AS o
    ON oi.order_id = o.order_id
INNER JOIN {db}.products AS p
    ON oi.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue DESC, p.category"""
    )


def assembler_workload(client, db):
    """Нагрузка на сборщиков."""
    return client.query(
        f"""SELECT
    a.last_name AS assembler,
    sum(oi.quantity) AS assembled_units,
    sum(oi.quantity * oi.unit_price) AS order_amount
FROM {db}.assemblers AS a
INNER JOIN {db}.order_items AS oi
    ON a.assembler_id = oi.assembler_id
GROUP BY a.assembler_id, a.last_name
ORDER BY assembled_units DESC, order_amount DESC"""
    )


def workshop_workload(client, db):
    """Загрузка производственных цехов."""
    return client.query(
        f"""SELECT
    w.name AS workshop,
    sum(oi.quantity) AS units,
    sum(oi.quantity * oi.unit_price) AS amount
FROM {db}.workshops AS w
INNER JOIN {db}.products AS p
    ON w.workshop_id = p.workshop_id
INNER JOIN {db}.order_items AS oi
    ON p.product_id = oi.product_id
GROUP BY w.workshop_id, w.name
ORDER BY amount DESC"""
    )


def overdue_orders(client, db, as_of=date(2026, 5, 1), days=14):
    """Незавершённые заказы старше 14 дней на 01.05.2026."""
    return client.query(
        f"""SELECT
    order_id,
    customer_id,
    order_date,
    dateDiff('day', order_date, {{as_of:Date}})
        AS days_open
FROM {db}.orders
WHERE status = 'in_progress'
  AND dateDiff('day', order_date,
               {{as_of:Date}}) > {{days:UInt32}}
ORDER BY days_open DESC""", parameters={"as_of": as_of, "days": days}
    )


def customer_activity(client, db):
    """Активность покупателей."""
    return client.query(
        f"""SELECT
    c.last_name AS customer,
    uniqExactIf(o.order_id, o.order_id != 0) AS orders,
    sum(oi.quantity * oi.unit_price) AS total_amount
FROM {db}.customers AS c
LEFT JOIN {db}.orders AS o
    ON c.customer_id = o.customer_id
LEFT JOIN {db}.order_items AS oi
    ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.last_name
ORDER BY total_amount DESC, customer"""
    )


def unordered_products(client, db):
    """Изделия, не включённые в заказы."""
    return client.query(
        f"""SELECT product_id, name, category, base_price
FROM {db}.products
WHERE product_id NOT IN
(
    SELECT DISTINCT product_id
    FROM {db}.order_items
)
ORDER BY product_id"""
    )


REPORTS = [
    (orders_in_period, 'Заказы за февраль и март 2026 года', ['Заказ', 'Покупатель ID', 'Дата заказа', 'Статус']),
    (order_details, 'Состав заказа № 101', ['Заказ', 'Покупатель', 'Изделие', 'Сборщик', 'Кол-во', 'Сумма, руб.']),
    (order_totals, 'Стоимость каждого заказа', ['Заказ', 'Покупатель', 'Сумма, руб.']),
    (monthly_revenue, 'Выручка по месяцам завершения заказов', ['Месяц', 'Заказов', 'Выручка, руб.']),
    (category_revenue, 'Выручка по категориям мебели', ['Категория', 'Изделий', 'Выручка, руб.']),
    (assembler_workload, 'Нагрузка на сборщиков', ['Сборщик', 'Изделий', 'Сумма, руб.']),
    (workshop_workload, 'Загрузка производственных цехов', ['Цех', 'Изделий', 'Сумма, руб.']),
    (overdue_orders, 'Незавершённые заказы старше 14 дней на 01.05.2026', ['Заказ', 'Покупатель ID', 'Дата заказа', 'Дней']),
    (customer_activity, 'Активность покупателей', ['Покупатель', 'Заказов', 'Сумма, руб.']),
    (unordered_products, 'Изделия, не включённые в заказы', ['ID', 'Изделие', 'Категория', 'Цена, руб.']),
]
