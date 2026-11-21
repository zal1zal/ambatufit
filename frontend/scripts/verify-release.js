const fs = require('fs');
const { URL } = require('url');
const config = require('../app.json').expo;
const errors = [];
for (const [key, suffix] of [
  ['EXPO_PUBLIC_API_BASE_URL', '/api/v1'],
  ['EXPO_PUBLIC_INTEGRATION_API_BASE_URL', '/integration/v1'],
]) {
  try {
    const url = new URL(process.env[key]);
    if (
      url.protocol !== 'https:' ||
      !url.pathname.endsWith(suffix) ||
      /localhost|\.invalid$/.test(url.hostname)
    )
      errors.push(`${key}: approved production HTTPS host required`);
  } catch {
    errors.push(`${key}: production URL missing`);
  }
}
const splashPlugin = config.plugins.find(
  (entry) => Array.isArray(entry) && entry[0] === 'expo-splash-screen',
);
for (const path of [config.icon, splashPlugin?.[1]?.image])
  if (!path || !fs.existsSync(path)) errors.push('App icon or splash asset missing');
if (errors.length) {
  process.stderr.write(errors.join('\n') + '\n');
  process.exitCode = 1;
} else
  process.stdout.write(
    'Release URLs and artwork configured. EAS credentials and Android installation still require verification.\n',
  );
