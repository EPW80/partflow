# PartFlow Airflow image: base Airflow + an isolated dbt virtualenv.
# dbt lives in its own venv (/opt/dbt-venv) so its dependencies never collide with
# Airflow's constraint-pinned environment (ADR-0003). The DAG's BashOperator invokes
# /opt/dbt-venv/bin/dbt.
FROM apache/airflow:2.10.4

USER root
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/dbt-venv/bin/pip install --no-cache-dir "dbt-postgres==1.9.0" \
    && chmod -R a+rx /opt/dbt-venv

USER airflow
