"""Схема шести таблиц из ЛР5, вариант 20."""

SCHEMA = {
    "customers": """CREATE TABLE IF NOT EXISTS {db}.customers
(
    customer_id UInt32,
    last_name String,
    address String
)
ENGINE = MergeTree
ORDER BY customer_id""",
    "workshops": """CREATE TABLE IF NOT EXISTS {db}.workshops
(
    workshop_id UInt32,
    name String,
    specialization String
)
ENGINE = MergeTree
ORDER BY workshop_id""",
    "assemblers": """CREATE TABLE IF NOT EXISTS {db}.assemblers
(
    assembler_id UInt32,
    last_name String,
    experience_years UInt8
)
ENGINE = MergeTree
ORDER BY assembler_id""",
    "products": """CREATE TABLE IF NOT EXISTS {db}.products
(
    product_id UInt32,
    name String,
    category LowCardinality(String),
    workshop_id UInt32,
    base_price Decimal(12, 2)
)
ENGINE = MergeTree
ORDER BY (workshop_id, product_id)""",
    "orders": """CREATE TABLE IF NOT EXISTS {db}.orders
(
    order_id UInt32,
    customer_id UInt32,
    order_date Date,
    completed_date Nullable(Date),
    status LowCardinality(String)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(order_date)
ORDER BY (order_date, order_id)""",
    "order_items": """CREATE TABLE IF NOT EXISTS {db}.order_items
(
    item_id UInt32,
    order_id UInt32,
    product_id UInt32,
    assembler_id UInt32,
    quantity UInt8,
    unit_price Decimal(12, 2)
)
ENGINE = MergeTree
ORDER BY (order_id, item_id)""",
}
