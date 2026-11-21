const fs = require('fs');
const path = require('path');
const Ajv2020 = require('ajv/dist/2020');
const addFormats = require('ajv-formats');
const load = require('./load-source')();
const schemas = load(path.resolve(__dirname, '../src/contracts/schemas.js'));
const root = path.resolve(__dirname, '../src/contracts');
const operations = require('../src/contracts/operations.json');
const api = fs.readFileSync(path.resolve(__dirname, '../src/services/ApiService.js'), 'utf8');
const documents = {
  core: JSON.parse(fs.readFileSync(path.join(root, 'openapi.json'), 'utf8')),
  integration: JSON.parse(fs.readFileSync(path.join(root, 'integration-openapi.json'), 'utf8')),
};
let fixtures = 0;
for (const entry of operations) {
  const document = documents[entry.service];
  const operation = document.paths[entry.path]?.[entry.method];
  if (!operation) throw Error(`OpenAPI missing ${entry.method} ${entry.path}`);
  const prefix = entry.service === 'core' ? '/api/v1' : '/integration/v1';
  const staticPath = entry.path.slice(prefix.length).split('/{')[0];
  if (!api.includes(staticPath)) throw Error(`ApiService missing ${staticPath}`);
  const response = Object.entries(operation.responses).find(([code]) => /^2\d\d$/.test(code))?.[1];
  for (const direction of ['request', 'response']) {
    const schemaName = entry[`${direction}Schema`];
    if (!schemaName) continue;
    const guard = schemas[schemaName];
    if (!guard) throw Error(`Missing client validator: ${schemaName}`);
    const spec = direction === 'request' ? operation.requestBody?.content?.['application/json']?.schema : response?.content?.['application/json']?.schema;
    if (!spec) throw Error(`OpenAPI missing ${direction} schema for ${entry.path}`);
    const ajv = new Ajv2020({ strict: false, allErrors: true });
    addFormats(ajv);
    const validate = ajv.compile({ ...spec, components: document.components });
    const fixtureName = entry[`${direction}Fixture`];
    if (!fixtureName) throw Error(`Missing ${direction} fixture for ${entry.method} ${entry.path}`);
    const value = JSON.parse(fs.readFileSync(path.join(root, 'examples', fixtureName), 'utf8'));
    if (!validate(value)) throw Error(`OpenAPI rejects ${fixtureName}: ${ajv.errorsText(validate.errors)}`);
    const parsed = guard.safeParse(value);
    if (!parsed.success) throw Error(`Client rejects ${fixtureName}: ${parsed.error.message}`);
    fixtures++;
  }
}
console.log(`Verified ${operations.length} HTTP operations and ${fixtures} request/response fixtures against OpenAPI + client Zod validators (frontend-local files only).`);