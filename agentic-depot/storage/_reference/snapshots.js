import { upsertEntity, getEntity, listAll, batchUpsert, TABLES } from './client.js';
import { odata } from '@azure/data-tables';

// Snapshot + Positionen speichern (atomisch aus Sicht des Callers)
export async function saveSnapshot(snapshot, positions) {
  // Snapshot speichern
  await upsertEntity(TABLES.SNAPSHOTS, {
    partitionKey: snapshot.broker,
    rowKey: snapshot.snapshot_id,
    timestamp_berlin: snapshot.timestamp_berlin,
    depot_id: snapshot.depot_id ?? '',
    portfolio_value_eur: snapshot.portfolio_value_eur,
    source_format: snapshot.source_format,
    notes: snapshot.notes ?? '',
  });

  // Positionen als Batch speichern
  const positionEntities = positions.map(p => ({
    partitionKey: snapshot.snapshot_id,
    rowKey: p.instrument_key,
    isin: p.isin ?? '',
    wkn: p.wkn ?? '',
    name_raw: p.name_raw,
    broker_source: p.broker_source ?? snapshot.broker,
    asset_class: p.asset_class ?? '',
    region: p.region ?? '',
    sector: p.sector ?? '',
    theme: p.theme ?? '',
    quantity: p.quantity,
    price: p.price,
    entry_price: p.entry_price ?? 0,
    purchase_value_eur: p.purchase_value_eur ?? 0,
    market_value_eur: p.market_value_eur,
    unreal_pl_eur: p.unreal_pl_eur ?? 0,
    unreal_pl_pct: p.unreal_pl_pct ?? 0,
    currency: p.currency ?? 'EUR',
  }));

  await batchUpsert(TABLES.POSITIONS, positionEntities);
  console.log(`[snapshots] Gespeichert: ${snapshot.snapshot_id} (${positions.length} Positionen)`);
}

// Letzten Snapshot für einen Broker laden (oder nach snapshot_id)
export async function getSnapshotBundle(opts = {}) {
  const { snapshot_id, broker } = opts;

  if (snapshot_id) {
    // Gezielt nach snapshot_id suchen
    const allSnapshots = await listAll(TABLES.SNAPSHOTS);
    const snapshot = allSnapshots.find(s => s.rowKey === snapshot_id) ?? null;
    if (!snapshot) return null;
    const positions = await listAll(TABLES.POSITIONS, odata`PartitionKey eq ${snapshot_id}`);
    return { snapshot: normalizeSnapshot(snapshot), positions: positions.map(normalizePosition) };
  }

  // Letzten Snapshot finden (nach timestamp_berlin sortiert)
  let filter = null;
  if (broker) filter = odata`PartitionKey eq ${broker}`;
  const allSnapshots = await listAll(TABLES.SNAPSHOTS, filter);
  if (allSnapshots.length === 0) return null;

  allSnapshots.sort((a, b) => b.timestamp_berlin.localeCompare(a.timestamp_berlin));
  const latest = allSnapshots[0];
  const positions = await listAll(TABLES.POSITIONS, odata`PartitionKey eq ${latest.rowKey}`);
  return { snapshot: normalizeSnapshot(latest), positions: positions.map(normalizePosition) };
}

// Alle Snapshots (für Historie)
export async function listSnapshots(broker = null) {
  let filter = null;
  if (broker) filter = odata`PartitionKey eq ${broker}`;
  const snapshots = await listAll(TABLES.SNAPSHOTS, filter);
  snapshots.sort((a, b) => b.timestamp_berlin.localeCompare(a.timestamp_berlin));
  return snapshots.map(normalizeSnapshot);
}

function normalizeSnapshot(entity) {
  return {
    snapshot_id: entity.rowKey,
    broker: entity.partitionKey,
    timestamp_berlin: entity.timestamp_berlin,
    depot_id: entity.depot_id,
    portfolio_value_eur: entity.portfolio_value_eur,
    source_format: entity.source_format,
    notes: entity.notes,
  };
}

function normalizePosition(entity) {
  return {
    instrument_key: entity.rowKey,
    snapshot_id: entity.partitionKey,
    isin: entity.isin,
    wkn: entity.wkn,
    name_raw: entity.name_raw,
    broker_source: entity.broker_source,
    asset_class: entity.asset_class,
    region: entity.region,
    sector: entity.sector,
    theme: entity.theme,
    quantity: entity.quantity,
    price: entity.price,
    entry_price: entity.entry_price,
    purchase_value_eur: entity.purchase_value_eur,
    market_value_eur: entity.market_value_eur,
    unreal_pl_eur: entity.unreal_pl_eur,
    unreal_pl_pct: entity.unreal_pl_pct,
    currency: entity.currency,
  };
}
