from datetime import datetime
from typing import List, Optional, Type

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit
from rainforest.utils.base_table import ETLDataSet, TableETL


class BuyerBronzeETL(TableETL):
    def __init__(
        self,
        spark: SparkSession,
        upstream_table_names: Optional[List[Type[TableETL]]] = None,
        name: str = "buyer",
        primary_keys: List[str] = ["buyer_id"],
        storage_path: str = "s3a://rainforest/delta/bronze/buyer",
        data_format: str = "delta",
        database: str = "rainforest",
        partition_keys: List[str] = ["etl_inserted"],
        run_upstream: bool = True,
    ) -> None:
        super().__init__(
            spark,
            upstream_table_names,
            name,
            primary_keys,
            storage_path,
            data_format,
            database,
            partition_keys,
            run_upstream,
        )

    def extract_upstream(self) -> List[ETLDataSet]:
        # Assuming buyer data is extracted from a database or other source
        # and loaded into a DataFrame
        jdbc_url = "jdbc:postgresql://upstream:5432/upstreamdb"
        connection_properties = {
            "user": "sdeuser",
            "password": "sdepassword",
            "driver": "org.postgresql.Driver",
        }
        table_name = "rainforest.buyer"
        buyer_data = self.spark.read.jdbc(
            url=jdbc_url, table=table_name, properties=connection_properties
        )

        # Create an ETLDataSet instance
        etl_dataset = ETLDataSet(
            name=self.name,
            curr_data=buyer_data,
            primary_keys=self.primary_keys,
            storage_path=self.storage_path,
            data_format=self.data_format,
            database=self.database,
            partition_keys=self.partition_keys,
        )

        return [etl_dataset]

    def transform_upstream(
        self, upstream_datasets: List[ETLDataSet]
    ) -> ETLDataSet:
        buyer_data = upstream_datasets[0].curr_data
        current_timestamp = datetime.now()

        # Perform any necessary transformations on the buyer data
        transformed_data = buyer_data.withColumn(
            "etl_inserted", lit(current_timestamp)
        )

        # Create a new ETLDataSet instance with the transformed data
        etl_dataset = ETLDataSet(
            name=self.name,
            curr_data=transformed_data,
            primary_keys=self.primary_keys,
            storage_path=self.storage_path,
            data_format=self.data_format,
            database=self.database,
            partition_keys=self.partition_keys,
        )

        return etl_dataset

    def validate(self, data: ETLDataSet) -> bool:
        # Perform any necessary validation checks on the buyer data
        return True

    def load(self, data: ETLDataSet) -> None:
        buyer_data = data.curr_data

        # Write the buyer data to the Delta Lake table
        buyer_data.write.format(data.data_format).mode(
            "overwrite"
        ).partitionBy(data.partition_keys).save(data.storage_path)

    def read(self, partition_keys: Optional[List[str]] = None) -> ETLDataSet:
        # Read the buyer data from the Delta Lake table
        buyer_data = self.spark.read.format(self.data_format).load(
            self.storage_path
        )
        # Explicitly select columns
        buyer_data = buyer_data.select(
            col("buyer_id"),
            col("user_id"),
            col("first_time_purchased_timestamp"),
            col("created_ts"),
            col("last_updated_by"),
            col("last_updated_ts"),
            col("etl_inserted"),
        )

        # Create an ETLDataSet instance
        etl_dataset = ETLDataSet(
            name=self.name,
            curr_data=buyer_data,
            primary_keys=self.primary_keys,
            storage_path=self.storage_path,
            data_format=self.data_format,
            database=self.database,
            partition_keys=self.partition_keys,
        )

        return etl_dataset
