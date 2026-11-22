import React, { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ROUTES, STACK_ROUTES } from './routeNames';
import AppTabs from './AppTabs';
import { tokens } from '../theme/tokens';
import {
  AssessmentResultScreen,
  AssessmentHistoryScreen,
  AssistantChatScreen,
  DiseaseSearchScreen,
  DiseaseDetailScreen,
  PersonalizedPlanScreen,
  MedicationsScreen,
  MedicationDetailScreen,
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
  AssistantChat: AssistantChatScreen,
  DiseaseSearch: DiseaseSearchScreen,
  DiseaseDetail: DiseaseDetailScreen,
  PersonalizedPlan: PersonalizedPlanScreen,
  Medications: MedicationsScreen,
  MedicationDetail: MedicationDetailScreen,
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
  const [reduceMotion, setReduceMotion] = useState(false);
  useEffect(() => {
    let active = true;
    AccessibilityInfo?.isReduceMotionEnabled?.()
      .then((val) => {
        if (active && val) setReduceMotion(true);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: tokens.color.background },
        animation: reduceMotion ? 'none' : 'slide_from_right',
      }}
    >
      <Stack.Screen name={ROUTES.Home} component={AppTabs} />
      {STACK_ROUTES.map((name) => (
        <Stack.Screen key={name} name={name} component={map[name]} />
      ))}
    </Stack.Navigator>
  );
}
