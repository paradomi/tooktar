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
import { Asset } from 'expo-asset';

// 패키지 metadata.json 의 공식 Google Fonts URL — 로컬 자산 해석 실패 시 폴백
const GSTATIC: Record<string, string> = {
  GowunBatang_400Regular:
    'https://fonts.gstatic.com/s/gowunbatang/v12/ijwSs5nhRMIjYsdSgcMa3wRhXLH-yuAtLw.ttf',
  GowunBatang_700Bold:
    'https://fonts.gstatic.com/s/gowunbatang/v12/ijwNs5nhRMIjYsdSgcMa3wRZ4J7awssxJii23w.ttf',
};

function resolveFontUri(family: string, mod: unknown): string {
  if (typeof mod === 'string') return mod; // 이미 URL 문자열
  try {
    const uri = Asset.fromModule(mod as number).uri; // 번들 자산 → URL (dev/prod 모두)
    if (uri) return uri;
  } catch {
    // fall through
  }
  return GSTATIC[family];
}

const webFontInjected = (() => {
  if (Platform.OS !== 'web' || typeof document === 'undefined') return false;
  const mods: [string, unknown][] = [
    ['GowunBatang_400Regular', GowunBatang_400Regular],
    ['GowunBatang_700Bold', GowunBatang_700Bold],
  ];
  const css = mods
    .map(([family, mod]) => {
      const uri = resolveFontUri(family, mod);
      const srcs = [uri, GSTATIC[family]]
        .filter((u, i, arr) => u && arr.indexOf(u) === i) // 중복 제거
        .map((u) => `url('${u}') format('truetype')`)
        .join(',');
      return `@font-face{font-family:'${family}';src:${srcs};font-display:swap;}`;
    })
    .join('\n');
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
