-- Suppliers: cast raw TEXT to typed columns. 1:1 with raw_suppliers.
select
    supplier_id,
    supplier_name,
    country,
    tier,
    category,
    promised_lead_time_days::int as promised_lead_time_days,
    onboarded_date::date         as onboarded_date
from {{ source('raw', 'raw_suppliers') }}
