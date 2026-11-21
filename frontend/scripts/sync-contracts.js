// Explicit maintenance command only; frontend run/tests never read backend files.
const fs = require('fs');
const path = require('path');
const source = process.argv[2];
if (!source) throw Error('Usage: node scripts/sync-contracts.js <backend-contracts-directory>');
const destination = path.resolve(__dirname, '../src/contracts');
for (const name of ['openapi.json', 'integration-openapi.json']) {
  const schema = JSON.parse(fs.readFileSync(path.join(source, name), 'utf8'));
  if (!schema.openapi || !schema.paths) throw Error(`Invalid schema: ${name}`);
  fs.copyFileSync(path.join(source, name), path.join(destination, name));
}
fs.cpSync(path.join(source, 'examples'), path.join(destination, 'examples'), { recursive: true });
console.log('Copied versioned OpenAPI and synthetic fixtures. Run npm run verify:contracts.');
