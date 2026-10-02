"""Daily refresh: regenerate data -> quality checks -> dbt models + tests -> static dashboard snapshot."""
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = os.getenv('VOICEIQ_PROJECT_DIR', '/opt/voiceiq')
DBT_DIR = os.path.join(PROJECT_DIR, 'dbt')

with DAG(
    dag_id='product_analytics_daily',
    start_date=datetime(2026, 1, 1),
    schedule='0 7 * * *',
    catchup=False,
    tags=['product-analytics', 'voiceiq'],
) as dag:
    # In production this would pull from the event warehouse; here it regenerates the synthetic tables.
    ingest = BashOperator(task_id='ingest_events', bash_command='python build_data.py', cwd=PROJECT_DIR)
    quality = BashOperator(task_id='data_quality', bash_command='python tests/test_data_quality.py', cwd=PROJECT_DIR)
    transform = BashOperator(task_id='dbt_build', bash_command='dbt build', cwd=DBT_DIR)  # runs models and tests
    refresh = BashOperator(task_id='refresh_dashboard_snapshot', bash_command='python export_static.py', cwd=PROJECT_DIR)
    ingest >> quality >> transform >> refresh
