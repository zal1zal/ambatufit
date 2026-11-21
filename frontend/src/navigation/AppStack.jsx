import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ROUTES, STACK_ROUTES } from './routeNames';
import AppTabs from './AppTabs';
import { tokens } from '../theme/tokens';
import {
  AssessmentResultScreen,
  AssessmentHistoryScreen,
  HealthProfileEditScreen,
  NutritionScreen,
  GymsScreen,
  ProfessionalsScreen,
  ProfessionalDetailScreen,
  BookingScreen,
  MyBookingsScreen,
  ProfessionalSharedAssessmentScreen,
} from '../screens/AppScreens';
const Stack = createNativeStackNavigator();
const map = {
  AssessmentResult: AssessmentResultScreen,
  AssessmentHistory: AssessmentHistoryScreen,
  HealthProfileEdit: HealthProfileEditScreen,
  Nutrition: NutritionScreen,
  Gyms: GymsScreen,
  Professionals: ProfessionalsScreen,
  ProfessionalDetail: ProfessionalDetailScreen,
  Booking: BookingScreen,
  MyBookings: MyBookingsScreen,
  ProfessionalSharedAssessment: ProfessionalSharedAssessmentScreen,
};
export default function AppStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: tokens.color.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name={ROUTES.Home} component={AppTabs} />
      {STACK_ROUTES.map((name) => (
        <Stack.Screen key={name} name={name} component={map[name]} />
      ))}
    </Stack.Navigator>
  );
}
