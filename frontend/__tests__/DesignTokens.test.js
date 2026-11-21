import { tokens } from '../src/theme/tokens';
test('uses Figma v2 colors and accessible hit target', () => {
  expect(tokens.color.primary).toBe('#F2DF3A');
  expect(tokens.color.surfaceDark).toBe('#182023');
  expect(tokens.color.background).toBe('#F4F5F1');
  expect(tokens.color.danger).toBe('#B42318');
  expect(tokens.layout.touchTargetMin).toBeGreaterThanOrEqual(44);
});
