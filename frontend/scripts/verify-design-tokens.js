const fs = require('fs'),
  path = require('path');
const root = path.resolve(__dirname, '..');
const source = JSON.parse(fs.readFileSync(path.join(root, 'design/design-tokens.json'), 'utf8'));
const theme = fs.readFileSync(path.join(root, 'src/theme/tokens.js'), 'utf8');
for (const [key, value] of Object.entries(source.color)) {
  if (!theme.includes('design-tokens.json')) throw Error('Theme must import the token source');
  if (!String(value).startsWith('#')) throw Error(`Invalid color ${key}`);
}
if (
  source.color.primary.toLowerCase() !== '#f2df3a' ||
  source.color.surfaceDark.toLowerCase() !== '#182023' ||
  source.color.background.toLowerCase() !== '#f4f5f1'
)
  throw Error('Figma v2 palette drifted');
console.log(
  `Design tokens verified: ${source.version}; ${Object.keys(source.color).length} colors.`,
);
