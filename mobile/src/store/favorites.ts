/** 자주 가는 곳 영구 저장 (AsyncStorage) + React 훅 */
import { useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FAVORITE_PLACES, type FavoritePlace } from '../data/favorites';

const KEY = 'tooktah:favorites:v1';

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoritePlace[]>(FAVORITE_PLACES);
  const [loaded, setLoaded] = useState(false);

  // 최초 로드
  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as FavoritePlace[];
          if (Array.isArray(parsed)) setFavorites(parsed);
        }
      } catch {
        // 실패 시 기본값 유지
      } finally {
        setLoaded(true);
      }
    })();
  }, []);

  const persist = useCallback(async (next: FavoritePlace[]) => {
    setFavorites(next);
    try {
      await AsyncStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      // 저장 실패는 무시 (메모리 상태는 유지됨)
    }
  }, []);

  const addFavorite = useCallback(
    (place: FavoritePlace) => persist([...favorites, place]),
    [favorites, persist]
  );

  const removeFavorite = useCallback(
    (index: number) => persist(favorites.filter((_, i) => i !== index)),
    [favorites, persist]
  );

  const updateFavorite = useCallback(
    (index: number, place: FavoritePlace) =>
      persist(favorites.map((p, i) => (i === index ? place : p))),
    [favorites, persist]
  );

  const reorderFavorites = useCallback(
    (next: FavoritePlace[]) => persist(next),
    [persist]
  );

  return { favorites, loaded, addFavorite, removeFavorite, updateFavorite, reorderFavorites };
}
