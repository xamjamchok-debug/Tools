import 'dotenv/config';
import { initStorage } from './storage/client.js';

console.log('Agentic Depot — Start...');

// Storage initialisieren (idempotent)
await initStorage();

console.log('Bereit. Block 3 (Workflows) folgt in nächster Session.');
// TODO Block 3: Express-Server + Orchestrator + Workflows
