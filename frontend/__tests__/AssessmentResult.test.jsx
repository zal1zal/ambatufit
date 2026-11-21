import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { View } from 'react-native';
import { SafetyNotice } from '../src/components/UI';
test('urgent safety notice has explicit accessible alert', () => {
  const view = render(
    <SafetyNotice level="urgent" message="Gejala mungkin memerlukan pertolongan medis segera." />,
  );
  expect(view.UNSAFE_getByType(View).props.accessibilityRole).toBe('alert');
  expect(screen.getByText('PENTING: BANTUAN MEDIS')).toBeTruthy();
});
