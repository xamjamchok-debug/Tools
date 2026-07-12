import { upsertEntity, listByPartition, listAll, TABLES } from './client.js';

// Alert-Konfiguration speichern
export async function saveAlertConfig(config) {
  const id = config.alert_id ?? `ALERT-${Date.now()}`;
  await upsertEntity(TABLES.ALERTS_CONFIG, {
    partitionKey: 'config',
    rowKey: id,
    instrument_key: config.instrument_key ?? '',
    condition: config.condition,
    alert_type: config.alert_type,
    severity: config.severity ?? 'warn',
    active: config.active ?? true,
  });
  return id;
}

export async function listActiveAlerts() {
  const all = await listByPartition(TABLES.ALERTS_CONFIG, 'config');
  return all.filter(a => a.active);
}

// Alert-Ereignis loggen
export async function logAlert(alertId, alertType, message, severity, instrumentKey = '') {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  await upsertEntity(TABLES.ALERT_LOG, {
    partitionKey: 'log',
    rowKey: `${ts}_${alertId}`,
    alert_id: alertId,
    timestamp_berlin: new Date().toLocaleString('de-DE', { timeZone: 'Europe/Berlin' }),
    alert_type: alertType,
    instrument_key: instrumentKey,
    message,
    severity,
    acknowledged: false,
  });
}

export async function listAlertLog(limit = 50) {
  const all = await listByPartition(TABLES.ALERT_LOG, 'log');
  all.sort((a, b) => b.rowKey.localeCompare(a.rowKey));
  return all.slice(0, limit);
}

export async function acknowledgeAlert(rowKey) {
  const all = await listByPartition(TABLES.ALERT_LOG, 'log');
  const entity = all.find(e => e.rowKey === rowKey);
  if (entity) {
    await upsertEntity(TABLES.ALERT_LOG, { ...entity, acknowledged: true });
  }
}
