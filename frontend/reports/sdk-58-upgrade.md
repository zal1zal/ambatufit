# SDK 58 upgrade

Upgraded Expo to ~58.0.26 with React 19.3.0 and React Native 0.88.1. Native dependencies, Babel preset, Jest and jest-expo were aligned using Expo install. React Test Renderer matches React 19.3.0. Node 24 LTS is recommended for this package.

Removed obsolete newArchEnabled config and StatusBar backgroundColor prop. Migrated legacy splash config to the expo-splash-screen plugin with the existing original artwork. Progress form test now explicitly flushes the initial async resource load before interaction under the updated test renderer.

Observed checks: Expo Doctor 20/20 passed; Jest 9 suites / 18 tests passed; Android JS export succeeded. No Android device is attached, so actual Expo Go SDK 58 interaction remains unverified. Existing live backend and release credential blockers remain.

Run from frontend: npm ci, then npx expo start --clear and scan using Expo Go SDK 58. A reachable configured backend and account are still required to log in.
