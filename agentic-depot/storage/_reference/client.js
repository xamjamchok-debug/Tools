import { TableServiceClient, TableClient, odata } from '@azure/data-tables';

const CONNECTION_STRING = process.env.AZURE_STORAGE_CONNECTION_STRING;

// Alle Tabellen des Datenmodells
export const TABLES = {
  SNAPSHOTS:     'snapshots',
  POSITIONS:     'positions',
  CASHFLOWS:     'cashflows',
  PRICE_UPDATES: 'priceupdates',
  ALERTS_CONFIG: 'alertsconfig',
  ALERT_LOG:     'alertlog',
  INCIDENTS:     'incidents',
};

// Idempotentes Anlegen aller Tabellen beim Start
export async function initStorage() {
  const serviceClient = TableServiceClient.fromConnectionString(CONNECTION_STRING);
  for (const tableName of Object.values(TABLES)) {
    try {
      await serviceClient.createTable(tableName);
      console.log(`[storage] Tabelle erstellt: ${tableName}`);
    } catch (err) {
      if (err.statusCode === 409) {
        // Tabelle existiert bereits — ok
      } else {
        throw err;
      }
    }
  }
  console.log('[storage] Storage initialisiert.');
}

function getClient(tableName) {
  return TableClient.fromConnectionString(CONNECTION_STRING, tableName);
}

// Entität upserten (anlegen oder überschreiben)
export async function upsertEntity(tableName, entity) {
  const client = getClient(tableName);
  await client.upsertEntity(entity, 'Replace');
}

// Einzelne Entität abrufen
export async function getEntity(tableName, partitionKey, rowKey) {
  const client = getClient(tableName);
  try {
    return await client.getEntity(partitionKey, rowKey);
  } catch (err) {
    if (err.statusCode === 404) return null;
    throw err;
  }
}

// Alle Entitäten einer Partition abrufen
export async function listByPartition(tableName, partitionKey) {
  const client = getClient(tableName);
  const results = [];
  const iter = client.listEntities({
    queryOptions: { filter: odata`PartitionKey eq ${partitionKey}` }
  });
  for await (const entity of iter) {
    results.push(entity);
  }
  return results;
}

// Alle Entitäten einer Tabelle abrufen (mit optionalem Filter)
export async function listAll(tableName, filter = null) {
  const client = getClient(tableName);
  const results = [];
  const options = filter ? { queryOptions: { filter } } : {};
  const iter = client.listEntities(options);
  for await (const entity of iter) {
    results.push(entity);
  }
  return results;
}

// Entität löschen
export async function deleteEntity(tableName, partitionKey, rowKey) {
  const client = getClient(tableName);
  await client.deleteEntity(partitionKey, rowKey);
}

// Batch-Upsert für mehrere Entitäten einer Partition (max 100 pro Batch)
export async function batchUpsert(tableName, entities) {
  if (entities.length === 0) return;
  const client = getClient(tableName);
  // Azure Table Storage erlaubt max 100 Operationen pro Batch
  const chunkSize = 100;
  for (let i = 0; i < entities.length; i += chunkSize) {
    const chunk = entities.slice(i, i + chunkSize);
    const transaction = client.createBatch(chunk[0].partitionKey);
    for (const entity of chunk) {
      transaction.upsertEntity(entity, 'Replace');
    }
    await transaction.submitBatch();
  }
}
