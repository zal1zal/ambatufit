process.env.EXPO_PUBLIC_API_BASE_URL = 'https://core.example.invalid/api/v1';
process.env.EXPO_PUBLIC_INTEGRATION_API_BASE_URL =
  'https://integration.example.invalid/integration/v1';

jest.mock('expo-camera', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    CameraView: (props) => React.createElement(View, { testID: 'expo-camera-view', ...props }),
    useCameraPermissions: () => [{ granted: true }, jest.fn()],
  };
});
