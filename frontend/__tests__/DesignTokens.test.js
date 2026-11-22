import { tokens } from '../src/theme/tokens';
import { typography } from '../src/theme/typography';
import { assets } from '../src/theme/assets';

test('uses Figma v2 colors and accessible hit target', () => {
  expect(tokens.color.primary).toBe('#F2DF3A');
  expect(tokens.color.surfaceDark).toBe('#182023');
  expect(tokens.color.background).toBe('#F4F5F1');
  expect(tokens.color.danger).toBe('#B42318');
  expect(tokens.layout.touchTargetMin).toBeGreaterThanOrEqual(44);
});

test('typography mirror matches Guide 03 Type/* specifications', () => {
  expect(typography['Type/Display'].fontSize).toBe(48);
  expect(typography['Type/PageTitle'].fontSize).toBe(36);
  expect(typography['Type/SectionTitle'].fontSize).toBe(28);
  expect(typography['Type/CardTitle'].fontSize).toBe(18);
  expect(typography['Type/Body'].fontSize).toBe(16);
  expect(typography['Type/BodySmall'].fontSize).toBe(14);
  expect(typography['Type/Button'].fontSize).toBe(16);
  expect(typography['Type/NavLabel'].fontSize).toBe(12);
  expect(typography['Type/TechnicalLabel'].fontSize).toBe(12);
  expect(typography['Type/MicroLabel'].fontSize).toBe(11);
  expect(typography['Type/Metric'].fontSize).toBe(38);
});

test('central asset registry exports all 10 PNGs including medicationPlaceholder', () => {
  expect(assets.appIcon).toBeDefined();
  expect(assets.splash).toBeDefined();
  expect(assets.logo).toBeDefined();
  expect(assets.onboarding).toBeDefined();
  expect(assets.emptyAssessments).toBeDefined();
  expect(assets.apiError).toBeDefined();
  expect(assets.professionalPlaceholder).toBeDefined();
  expect(assets.nutritionPlaceholder).toBeDefined();
  expect(assets.gymPlaceholder).toBeDefined();
  expect(assets.medicationPlaceholder).toBeDefined();
});

