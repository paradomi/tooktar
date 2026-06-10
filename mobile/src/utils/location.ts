/** 현재 위치(GPS) — expo-location.
 *  웹/네이티브 모두 동작. 권한 거부·실패 시 null 반환(호출측에서 기본값 fallback).
 */
import * as Location from 'expo-location';
import type { Coord } from '../api/client';

export async function getCurrentCoord(): Promise<{ lat: number; lng: number } | null> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return null;
    const pos = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    return { lat: pos.coords.latitude, lng: pos.coords.longitude };
  } catch {
    return null;
  }
}

/** 두 좌표 사이 거리(m) — Haversine */
export function distanceM(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number }
): number {
  const R = 6371000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** 실시간 위치 추적. 반환된 함수를 호출하면 중지. 권한 거부 시 null. */
export async function watchPosition(
  onUpdate: (c: { lat: number; lng: number }) => void
): Promise<(() => void) | null> {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return null;
    const sub = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, distanceInterval: 5, timeInterval: 3000 },
      (pos) => onUpdate({ lat: pos.coords.latitude, lng: pos.coords.longitude })
    );
    return () => sub.remove();
  } catch {
    return null;
  }
}
