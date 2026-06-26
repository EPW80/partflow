{#
  Use the custom +schema as the literal schema name (e.g. "staging", "marts")
  instead of dbt's default of prefixing it with the target schema
  ("analytics_staging"). Cleaner for a single-tenant warehouse where the web app
  and BI tools read a stable `marts` schema. Models without a custom schema fall
  back to the target schema.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
