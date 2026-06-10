/** 앱 설정(글자 크기) 전역 Context — 모든 화면이 같은 값을 구독 */
import React, { createContext, useContext, useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setGlobalFontScale } from './FontScaler';

const KEY = 'tooktah:settings:v1';

export type FontLevel = '작게' | '보통' | '크게' | '매우 크게';
export const FONT_LEVELS: FontLevel[] = ['작게', '보통', '크게', '매우 크게'];

/** 레벨 → 본문 글자 배율
 *  기본값 '보통'을 기존 '크게'(1.15)의 약 1.5배(≈1.7)로 상향. 단계별로 확대.
 */
export const FONT_SCALE: Record<FontLevel, number> = {
  작게: 1.4,
  보통: 1.7,
  크게: 2.0,
  '매우 크게': 2.3,
};

/** 앱 기본 글자 크기 레벨 */
export const DEFAULT_FONT_LEVEL: FontLevel = '보통';

interface SettingsCtx {
  fontLevel: FontLevel;
  scale: number;
  updateFontLevel: (level: FontLevel) => void;
}

const Ctx = createContext<SettingsCtx>({
  fontLevel: DEFAULT_FONT_LEVEL,
  scale: FONT_SCALE[DEFAULT_FONT_LEVEL],
  updateFontLevel: () => {},
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [fontLevel, setFontLevel] = useState<FontLevel>(DEFAULT_FONT_LEVEL);

  // 전역 배율을 즉시 반영 (Text.render 패치가 참조)
  const scale = FONT_SCALE[fontLevel];
  setGlobalFontScale(scale);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as { fontLevel?: FontLevel };
          if (parsed.fontLevel && FONT_LEVELS.includes(parsed.fontLevel)) {
            setFontLevel(parsed.fontLevel);
          }
        }
      } catch {
        // 기본값 유지
      }
    })();
  }, []);

  const updateFontLevel = useCallback((level: FontLevel) => {
    setGlobalFontScale(FONT_SCALE[level]);
    setFontLevel(level);
    AsyncStorage.setItem(KEY, JSON.stringify({ fontLevel: level })).catch(() => {});
  }, []);

  return (
    <Ctx.Provider value={{ fontLevel, scale, updateFontLevel }}>{children}</Ctx.Provider>
  );
}

export function useSettings() {
  return useContext(Ctx);
}

/** 배율을 적용한 글자 크기 헬퍼 */
export function useFontScale() {
  const { scale } = useSettings();
  return (size: number) => Math.round(size * scale);
}
