import { ROUTES, TAB_ROUTES, STACK_ROUTES } from '../src/navigation/routeNames';
test('has exactly the five required tab IDs', () =>
  expect(TAB_ROUTES).toEqual(['Home', 'SymptomAssessment', 'Guidance', 'Progress', 'Profile']));
test('detail IDs are declared', () => {
  expect(STACK_ROUTES.every((x) => ROUTES[x] === x)).toBe(true);
  expect(STACK_ROUTES).toContain('Booking');
  expect(STACK_ROUTES).toContain('Medications');
  expect(STACK_ROUTES).toContain('MedicationDetail');
});
