from collections import defaultdict
from typing import Optional
from azure.data.tables import TableServiceClient, TableClient
from .config import config


class AzureClient:
    """Generischer Azure Table Storage Wrapper. Niemals das SDK direkt aufrufen."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._conn = config.azure_connection_string

    def _t(self, name: str) -> str:
        return f"{self.prefix}{name}"

    def init_storage(self, table_names: list[str]) -> None:
        """Legt alle Tabellen idempotent an."""
        svc = TableServiceClient.from_connection_string(self._conn)
        for name in table_names:
            try:
                svc.create_table(self._t(name))
                print(f"[azure] Tabelle erstellt: {self._t(name)}")
            except Exception as e:
                if getattr(e, "status_code", None) == 409:
                    pass  # already exists
                else:
                    raise

    def upsert(self, table: str, entity: dict) -> None:
        TableClient.from_connection_string(self._conn, self._t(table)).upsert_entity(
            entity, mode="replace"
        )

    def get(self, table: str, partition_key: str, row_key: str) -> Optional[dict]:
        try:
            return dict(
                TableClient.from_connection_string(self._conn, self._t(table)).get_entity(
                    partition_key, row_key
                )
            )
        except Exception as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise

    def list_by_partition(self, table: str, partition_key: str) -> list[dict]:
        client = TableClient.from_connection_string(self._conn, self._t(table))
        return [dict(e) for e in client.query_entities(f"PartitionKey eq '{partition_key}'")]

    def list_all(self, table: str, filter: Optional[str] = None) -> list[dict]:
        client = TableClient.from_connection_string(self._conn, self._t(table))
        kwargs = {"query_filter": filter} if filter else {}
        return [dict(e) for e in client.list_entities(**kwargs)]

    def delete(self, table: str, partition_key: str, row_key: str) -> None:
        TableClient.from_connection_string(self._conn, self._t(table)).delete_entity(
            partition_key, row_key
        )

    def batch_upsert(self, table: str, entities: list[dict]) -> None:
        if not entities:
            return
        # Azure erlaubt max 100 Ops pro Batch, alle mit gleichem PartitionKey
        by_pk: dict[str, list] = defaultdict(list)
        for e in entities:
            by_pk[e["partitionKey"]].append(e)

        client = TableClient.from_connection_string(self._conn, self._t(table))
        for pk_entities in by_pk.values():
            for i in range(0, len(pk_entities), 100):
                chunk = pk_entities[i : i + 100]
                ops = [("upsert", e, {"mode": "replace"}) for e in chunk]
                client.submit_transaction(ops)
