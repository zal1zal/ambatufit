const fs = require('fs'),
  path = require('path');
const api = fs.readFileSync(path.resolve(__dirname, '../src/services/ApiService.js'), 'utf8');
const paths = [
  '/auth/login',
  '/auth/me',
  '/profile',
  '/assessments/evidences',
  '/assessments',
  '/guidance',
  '/monitoring/entries',
  '/professionals',
  '/bookings',
  '/consents/assessment-sharing',
  '/nutrition/foods',
  '/fitness/gyms',
  '/system/capabilities',
  '/professional/bookings/',
];
const missing = paths.filter((p) => !api.includes(p));
if (missing.length) throw Error(`Missing API paths: ${missing.join(', ')}`);
if (
  !api.includes('EXPO_PUBLIC_API_BASE_URL') ||
  !api.includes('EXPO_PUBLIC_INTEGRATION_API_BASE_URL')
)
  throw Error('Missing base URL config');
console.log(
  `Contract route inventory verified (${paths.length} groups). OpenAPI not present; schema comparison remains blocked.`,
);
