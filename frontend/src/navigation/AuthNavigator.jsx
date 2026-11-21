import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ROUTES } from './routeNames';
import { LoginScreen } from '../screens/AppScreens';
const Stack = createNativeStackNavigator();
export default function AuthNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name={ROUTES.Login} component={LoginScreen} />
    </Stack.Navigator>
  );
}
