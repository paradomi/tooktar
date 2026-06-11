import 'react-native-gesture-handler';
import React, { useEffect } from 'react';
import { Platform } from 'react-native';
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

// 웹: expo-font 의 JS 로딩(6초 타임아웃, 느린 폰 네트워크에서 실패)에 의존하지 않고
// 브라우저 네이티브 @font-face(font-display: swap)로 등록 → 폰트가 도착하는 대로 적용.
// 첫 렌더 전에 실행되도록 모듈 스코프에서 주입.
const webFontInjected = (() => {
  if (Platform.OS !== 'web' || typeof document === 'undefined') return false;
  const urls: [string, unknown][] = [
    ['GowunBatang_400Regular', GowunBatang_400Regular],
    ['GowunBatang_700Bold', GowunBatang_700Bold],
  ];
  const css = urls
    .filter(([, u]) => typeof u === 'string')
    .map(
      ([family, u]) =>
        `@font-face{font-family:'${family}';src:url('${u}') format('truetype');font-display:swap;}`
    )
    .join('\n');
  if (!css) return false;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
  setFontReady(true); // 텍스트에 fontFamily 즉시 부여 (스왑은 브라우저가 처리)
  return true;
})();

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
  // 웹은 @font-face 주입으로 이미 준비됨 — 네이티브만 expo-font 로딩을 기다린다
  const ready = webFontInjected || fontsLoaded;

  useEffect(() => {
    if (ready) setFontReady(true);
  }, [ready]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <SettingsProvider>
          <Navigation fontsLoaded={ready} />
        </SettingsProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
