"""Illustrative orchestration only; this DAG is intentionally dependency-light."""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime

def refresh_dataset():
    print('Refresh browser-facing aggregate dataset here.')

with DAG(
    dag_id='product_analytics_daily',
    start_date=datetime(2026, 1, 1),
    schedule='0 7 * * *',
    catchup=False,
    tags=['product-analytics','voiceiq'],
) as dag:
    ingest = PythonOperator(task_id='ingest_events', python_callable=lambda: print('Ingest new events'))
    transform = BashOperator(task_id='dbt_build', bash_command='dbt build')
    tests = BashOperator(task_id='dbt_test', bash_command='dbt test')
    refresh = PythonOperator(task_id='refresh_dashboard_dataset', python_callable=refresh_dataset)
    ingest >> transform >> tests >> refresh
