-- Purchase order headers. 1:1 with raw_purchase_orders.
select
    po_id,
    supplier_id,
    order_date::date    as order_date,
    promised_date::date as promised_date,
    status
from {{ source('raw', 'raw_purchase_orders') }}
