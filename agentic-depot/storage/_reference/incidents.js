import { upsertEntity, listByPartition, getEntity, TABLES } from './client.js';

export async function createIncident(incident) {
  const id = `INC-${Date.now()}`;
  await upsertEntity(TABLES.INCIDENTS, {
    partitionKey: 'incidents',
    rowKey: id,
    created_at: new Date().toISOString(),
    snapshot_id: incident.snapshot_id ?? '',
    type: incident.type,
    name_raw: incident.name_raw ?? '',
    details: incident.details ?? '',
    status: 'open',
    resolution: '',
  });
  console.log(`[incidents] Incident erstellt: ${id} (${incident.type})`);
  return id;
}

export async function listOpenIncidents() {
  const all = await listByPartition(TABLES.INCIDENTS, 'incidents');
  return all.filter(i => i.status === 'open');
}

export async function listAllIncidents() {
  return listByPartition(TABLES.INCIDENTS, 'incidents');
}

export async function closeIncident(incidentId, resolution, closedBy = 'user') {
  const entity = await getEntity(TABLES.INCIDENTS, 'incidents', incidentId);
  if (!entity) throw new Error(`Incident ${incidentId} nicht gefunden`);
  await upsertEntity(TABLES.INCIDENTS, {
    ...entity,
    status: closedBy === 'system' ? 'closed_by_system' : 'closed_by_user',
    resolution,
  });
}

export async function resolveIncidentAuto(incidentId, resolution) {
  const entity = await getEntity(TABLES.INCIDENTS, 'incidents', incidentId);
  if (!entity) throw new Error(`Incident ${incidentId} nicht gefunden`);
  await upsertEntity(TABLES.INCIDENTS, {
    ...entity,
    status: 'auto_resolved',
    resolution,
  });
}
