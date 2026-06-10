import 'react-native-gesture-handler';
import React, { useEffect } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import {
  useFonts,
  GowunBatang_400Regular,
  GowunBatang_700Bold,
} from '@expo-google-fonts/gowun-batang';
import HomeScreen from './src/screens/HomeScreen';
import RoutesScreen from './src/screens/RoutesScreen';
import DetailScreen from './src/screens/DetailScreen';
import GuideScreen from './src/screens/GuideScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { SettingsProvider, useSettings } from './src/store/SettingsContext';
import { setFontReady } from './src/store/FontScaler';
import type { RootStackParamList } from './src/navigation/types';

const Stack = createNativeStackNavigator<RootStackParamList>();

function Navigation({ fontsLoaded }: { fontsLoaded: boolean }) {
  // scale·폰트 로드 상태가 바뀌면 Navigator 를 리마운트해 모든 화면 Text 가 다시 그려진다.
  const { scale } = useSettings();
  return (
    <NavigationContainer>
      <Stack.Navigator
        key={`fs-${scale}-${fontsLoaded ? 'f1' : 'f0'}`}
        screenOptions={{ headerShown: false }}
      >
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Routes" component={RoutesScreen} />
        <Stack.Screen name="Detail" component={DetailScreen} />
        <Stack.Screen name="Guide" component={GuideScreen} />
        <Stack.Screen name="Settings" component={SettingsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    GowunBatang_400Regular,
    GowunBatang_700Bold,
  });

  useEffect(() => {
    if (fontsLoaded) setFontReady(true);
  }, [fontsLoaded]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <SettingsProvider>
          <Navigation fontsLoaded={fontsLoaded} />
        </SettingsProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
