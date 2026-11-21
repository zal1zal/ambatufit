import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { useAuth } from '../state/AuthContext';
import AuthNavigator from './AuthNavigator';
import AppStack from './AppStack';
import { tokens } from '../theme/tokens';
import { ScreenShell, ScreenState } from '../components/UI';
export default function RootNavigator() {
  const { ready, user, startupError, retryStartup } = useAuth();
  if (!ready)
    return (
      <View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: tokens.color.background,
        }}
      >
        <ActivityIndicator color={tokens.color.text} />
      </View>
    );
  if (startupError) return (
    <ScreenShell>
      <ScreenState title="Layanan belum dapat dihubungi" message={startupError} action="Coba lagi" onPress={retryStartup} />
    </ScreenShell>
  );
  return (
    <NavigationContainer key={user ? 'signed-in' : 'signed-out'}>
      {user ? <AppStack /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
