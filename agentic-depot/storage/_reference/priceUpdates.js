import { upsertEntity, listAll, batchUpsert, TABLES } from './client.js';
import { odata } from '@azure/data-tables';

export async function savePriceUpdates(updates) {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const entities = updates.map(u => ({
    partitionKey: u.instrument_key,
    rowKey: ts,
    price: u.price,
    change_pct_1d: u.change_pct_1d ?? 0,
    source: u.source,
  }));
  await batchUpsert(TABLES.PRICE_UPDATES, entities);
}

// Letzte Preise für alle Instrumente
export async function getLatestPrices(instrumentKeys) {
  const result = {};
  for (const key of instrumentKeys) {
    const updates = await listAll(
      TABLES.PRICE_UPDATES,
      odata`PartitionKey eq ${key}`
    );
    if (updates.length > 0) {
      updates.sort((a, b) => b.rowKey.localeCompare(a.rowKey));
      result[key] = {
        price: updates[0].price,
        change_pct_1d: updates[0].change_pct_1d,
        source: updates[0].source,
        timestamp: updates[0].rowKey,
      };
    }
  }
  return result;
}

// Zeitreihe für ein Instrument (für Volatilitätsberechnung)
export async function getPriceHistory(instrumentKey, days = 60) {
  const updates = await listAll(
    TABLES.PRICE_UPDATES,
    odata`PartitionKey eq ${instrumentKey}`
  );
  updates.sort((a, b) => a.rowKey.localeCompare(b.rowKey));
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return updates
    .filter(u => new Date(u.rowKey.replace(/-/g, ':').replace('T', ' ')) >= cutoff)
    .map(u => ({ timestamp: u.rowKey, price: u.price }));
}
