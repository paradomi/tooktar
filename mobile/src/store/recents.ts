/** 최근 검색 목적지 영구 저장 (AsyncStorage) + 훅 */
import { useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { Coord } from '../api/client';

const KEY = 'tooktah:recents:v1';
const MAX = 8;

export function useRecents() {
  const [recents, setRecents] = useState<Coord[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as Coord[];
          if (Array.isArray(parsed)) setRecents(parsed);
        }
      } catch {
        // 무시
      }
    })();
  }, []);

  /** 목적지를 최근 목록 맨 앞에 추가 (중복 제거, 최대 MAX개) */
  const addRecent = useCallback((dest: Coord) => {
    if (!dest?.name) return;
    setRecents((prev) => {
      const filtered = prev.filter((r) => r.name !== dest.name || r.address !== dest.address);
      const next = [dest, ...filtered].slice(0, MAX);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  /** 특정 항목 하나 삭제 */
  const removeRecent = useCallback((target: Coord) => {
    setRecents((prev) => {
      const next = prev.filter(
        (r) => !(r.name === target.name && r.address === target.address)
      );
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  const clearRecents = useCallback(() => {
    setRecents([]);
    AsyncStorage.removeItem(KEY).catch(() => {});
  }, []);

  return { recents, addRecent, removeRecent, clearRecents };
}
