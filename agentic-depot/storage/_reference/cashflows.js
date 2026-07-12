import { batchUpsert, listAll, TABLES } from './client.js';
import { odata } from '@azure/data-tables';

export async function saveCashflows(cashflows) {
  const entities = cashflows.map((c, i) => ({
    partitionKey: c.broker,
    rowKey: `${c.date}_${c.instrument_key ?? 'none'}_${c.type}_${String(i).padStart(4, '0')}`,
    date: c.date,
    broker: c.broker,
    amount_eur: c.amount_eur,
    type: c.type,
    instrument_key: c.instrument_key ?? '',
    quantity: c.quantity ?? 0,
    price: c.price ?? 0,
    memo_raw: c.memo_raw ?? '',
  }));
  await batchUpsert(TABLES.CASHFLOWS, entities);
  console.log(`[cashflows] ${cashflows.length} Cashflows gespeichert.`);
}

export async function listCashflows(broker = null) {
  let filter = null;
  if (broker) filter = odata`PartitionKey eq ${broker}`;
  const results = await listAll(TABLES.CASHFLOWS, filter);
  results.sort((a, b) => b.date.localeCompare(a.date));
  return results;
}
