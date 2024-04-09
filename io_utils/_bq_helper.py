from google.cloud import bigquery, storage
import time
from io_utils import GoogleAuthHelper
import streamlit as st


@st.cache_data
class BQHelper:
    """Helper class for I/O with BigQuery"""

    @staticmethod
    def init_client():
        credentials = GoogleAuthHelper.get_credentials()
        return bigquery.Client(credentials=credentials, project=GoogleAuthHelper.get_project())

    @staticmethod
    def init_client_gcs():
        credentials = GoogleAuthHelper.get_credentials()
        return storage.Client(credentials=credentials, project=GoogleAuthHelper.get_project())

    @staticmethod
    def load_table_from_json(
        client, dataset, table_name, rows_to_load, write_disposition
    ):
        table_id = f"{client.project}.{dataset}.{table_name}"

        # Load data into the table
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )

        client.load_table_from_json(
            rows_to_load, table_id, job_config=job_config
        ).result()

        return

    @staticmethod
    def load_table_from_dataframe(bq_client, dataframe, destination_table, max_retries=3, nb_sec_between_retries=5):
        success = False
        cnt_retries = 0
        while not success and cnt_retries < max_retries:
            try:
                job = bq_client.load_table_from_dataframe(
                    dataframe, destination_table
                )

                # Wait for the load job to complete.
                job.result()
                success = True
            except Exception as e:
                success = False
                cnt_retries += 1
                if cnt_retries < max_retries:
                    print(f"Retry {cnt_retries} (on table `{destination_table}`)")
                else:
                    print(e)
                time.sleep(nb_sec_between_retries)

    @staticmethod
    def delete_all_from_table(bq_client, bq_table, max_retries=3, nb_sec_between_retries=5):
        success = False
        cnt_retries = 0
        while not success and cnt_retries < max_retries:
            try:
                delete_query = f'DELETE FROM `{bq_table}` WHERE true'
                delete_job = bq_client.query(delete_query)  # Make an API request.
                delete_job.result()

                success = True
            except Exception as e:
                success = False
                cnt_retries += 1
                if cnt_retries < max_retries:
                    print(f"Retry {cnt_retries}")
                time.sleep(nb_sec_between_retries)

    @staticmethod
    def perform_query(bq_client, sql_query, max_retries=3, nb_sec_between_retries=5):
        success = False
        cnt_retries = 0
        while not success and cnt_retries < max_retries:
            try:
                delete_job = bq_client.query(sql_query)  # Make an API request.
                delete_job.result()

                success = True
            except Exception as e:
                success = False
                cnt_retries += 1
                if cnt_retries < max_retries:
                    print(f"Retry {cnt_retries}")
                time.sleep(nb_sec_between_retries)

    @staticmethod
    def get_dataframe_from_table(bq_client, dataset, table_name, selected_fields):
        table = bigquery.TableReference.from_string(f'{bq_client.project}.{dataset}.{table_name}')
        rows = bq_client.list_rows(
            table,
            selected_fields=selected_fields
        )
        return rows.to_dataframe()

    @staticmethod
    def get_dataframe_from_query(bq_client, sql_query):
        return bq_client.query(sql_query).to_dataframe()
