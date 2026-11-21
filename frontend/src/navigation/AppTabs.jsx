import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { TAB_ROUTES, ROUTES } from './routeNames';
import {
  HomeScreen,
  SymptomAssessmentScreen,
  GuidanceScreen,
  ProgressScreen,
  ProfileScreen,
} from '../screens/AppScreens';
import { tokens } from '../theme/tokens';
import IconHome from '../../assets/icon-home.svg';
import IconAssessment from '../../assets/icon-assessment.svg';
import IconGuidance from '../../assets/icon-guidance.svg';
import IconProgress from '../../assets/icon-progress.svg';
import IconProfile from '../../assets/icon-profile.svg';
import { BottomTabItem } from '../components/UI';
const Tab = createBottomTabNavigator();
const map = {
  Home: HomeScreen,
  SymptomAssessment: SymptomAssessmentScreen,
  Guidance: GuidanceScreen,
  Progress: ProgressScreen,
  Profile: ProfileScreen,
};
const labels = {
  Home: 'Beranda',
  SymptomAssessment: 'Cek Gejala',
  Guidance: 'Panduan',
  Progress: 'Perkembangan',
  Profile: 'Profil',
};
const icons = {
  Home: IconHome,
  SymptomAssessment: IconAssessment,
  Guidance: IconGuidance,
  Progress: IconProgress,
  Profile: IconProfile,
};
export function TabBar({ state, descriptors: _descriptors, navigation }) {
  const inset = useSafeAreaInsets();
  return (
    <View
      style={{
        height: 96 + inset.bottom,
        flexDirection: 'row',
        backgroundColor: tokens.color.surface,
        borderTopColor: tokens.color.border,
        borderTopWidth: 1,
        paddingTop: 5,
        paddingBottom: 8 + inset.bottom,
      }}
    >
      {state.routes.map((route, index) => {
        const focused = state.index === index;
        const Icon = icons[route.name];
        return (
          <View key={route.key} style={{ flex: 1, minWidth: 44 }}>
            <BottomTabItem
              label={labels[route.name]}
              active={focused}
              icon={Icon}
              onPress={() => {
                const event = navigation.emit({
                  type: 'tabPress',
                  target: route.key,
                  canPreventDefault: true,
                });
                if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
              }}
            />
          </View>
        );
      })}
    </View>
  );
}
export default function AppTabs() {
  return (
    <Tab.Navigator
      initialRouteName={ROUTES.Home}
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{ headerShown: false }}
    >
      {TAB_ROUTES.map((name) => (
        <Tab.Screen key={name} name={name} component={map[name]} />
      ))}
    </Tab.Navigator>
  );
}
