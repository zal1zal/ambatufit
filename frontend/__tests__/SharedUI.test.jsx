import React from 'react';
import { render } from '@testing-library/react-native';
import { ServiceStatusNotice, uiStyles } from '../src/components/UI';
test('screen styles are initialized when imported', () => {
  expect(uiStyles.body.fontSize).toBe(16);
});
test('available provider does not display unavailable copy', () => {
  const view = render(<ServiceStatusNotice provider="AmbatuNoutrish" status="available" />);
  expect(view.queryByText(/sedang tidak tersedia/)).toBeNull();
});
