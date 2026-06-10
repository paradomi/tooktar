/** 탑승→하차 정류장 진행 화면.
 *  경유 정류장 세로 리스트 + 사용자 GPS(=차량 위치)로 현재 정류장 실시간 강조·마커.
 *  지하철은 GPS가 약해도 가장 가까운 역을 추정 강조.
 */
import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { distanceM } from '../utils/location';
import { colors, sizes } from '../theme';

export interface PassStop {
  name: string;
  lat: number;
  lng: number;
}

interface Props {
  stops: PassStop[];
  myPos: { lat: number; lng: number } | null;
  kind: 'bus' | 'subway';
  lineLabel: string; // "5번 버스" / "수인분당선"
  color: string; // 노선 색
}

export default function TransitProgressView({ stops, myPos, kind, lineLabel, color }: Props) {
  // 현재 위치에서 가장 가까운 정류장 인덱스 (= 차량 현재 위치 근사)
  const currentIdx = useMemo(() => {
    if (!myPos || stops.length === 0) return -1;
    let best = -1;
    let bestD = Infinity;
    stops.forEach((s, i) => {
      const d = distanceM(myPos, { lat: s.lat, lng: s.lng });
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    // 너무 멀면(아직 안 탔거나 GPS 불량) 강조 안 함
    return bestD <= 400 ? best : -1;
  }, [myPos, stops]);

  const total = stops.length;
  const remain = currentIdx >= 0 ? Math.max(total - 1 - currentIdx, 0) : null;

  if (total === 0) return null;

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>
          {kind === 'bus' ? '🚌' : '🚇'} {lineLabel} 탑승
        </Text>
        {remain != null && (
          <Text style={[styles.remain, { color }]}>
            하차까지 {remain}{kind === 'subway' ? '역' : '정거장'}
          </Text>
        )}
      </View>

      {stops.map((s, i) => {
        const isStart = i === 0;
        const isEnd = i === total - 1;
        const isCurrent = i === currentIdx;
        const passed = currentIdx >= 0 && i < currentIdx;
        return (
          <View key={`${s.name}-${i}`} style={styles.stopRow}>
            {/* 좌측 노선 라인 + 노드 */}
            <View style={styles.railCol}>
              {/* 위쪽 선 */}
              <View
                style={[
                  styles.railLine,
                  { backgroundColor: i === 0 ? 'transparent' : passed || isCurrent ? color : '#D5DBE0' },
                ]}
              />
              <View
                style={[
                  styles.node,
                  (isStart || isEnd) && styles.nodeTerm,
                  { borderColor: color },
                  (passed || isCurrent) && { backgroundColor: color },
                ]}
              />
              {/* 아래쪽 선 */}
              <View
                style={[
                  styles.railLine,
                  { backgroundColor: i === total - 1 ? 'transparent' : passed ? color : '#D5DBE0' },
                ]}
              />
              {/* 현재 위치 버스/열차 마커 */}
              {isCurrent && (
                <View style={[styles.vehicleMarker, { backgroundColor: color }]}>
                  <Text style={styles.vehicleEmoji}>{kind === 'bus' ? '🚌' : '🚇'}</Text>
                </View>
              )}
            </View>

            {/* 정류장 정보 */}
            <View style={styles.stopInfo}>
              <Text
                style={[
                  styles.stopName,
                  (isStart || isEnd) && styles.stopNameTerm,
                  isCurrent && { color, fontWeight: '800' },
                ]}
                numberOfLines={1}
              >
                {s.name}
              </Text>
              {isStart && <Text style={[styles.tag, styles.tagStart]}>승차</Text>}
              {isEnd && <Text style={[styles.tag, styles.tagEnd]}>하차</Text>}
              {isCurrent && !isStart && !isEnd && (
                <Text style={[styles.tag, { backgroundColor: color }]}>현재 위치</Text>
              )}
            </View>
          </View>
        );
      })}

      {currentIdx < 0 && (
        <Text style={styles.hint}>탑승 후 위치가 자동으로 표시됩니다.</Text>
      )}
    </View>
  );
}

const NODE = 16;
const styles = StyleSheet.create({
  wrap: { marginTop: 8 },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  title: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.navy },
  remain: { fontSize: sizes.fontSmall, fontWeight: '800' },
  stopRow: { flexDirection: 'row', minHeight: 46 },
  railCol: { width: 36, alignItems: 'center', position: 'relative' },
  railLine: { width: 4, flex: 1 },
  node: {
    width: NODE,
    height: NODE,
    borderRadius: NODE / 2,
    borderWidth: 3,
    backgroundColor: '#fff',
    position: 'absolute',
    top: '50%',
    marginTop: -NODE / 2,
  },
  nodeTerm: { width: NODE + 4, height: NODE + 4, borderRadius: (NODE + 4) / 2, marginTop: -(NODE + 4) / 2 },
  vehicleMarker: {
    position: 'absolute',
    left: -14,
    top: '50%',
    marginTop: -13,
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 2,
    borderColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 3,
  },
  vehicleEmoji: { fontSize: 13 },
  stopInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingLeft: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  stopName: { flex: 1, fontSize: sizes.fontSmall, color: colors.darkText },
  stopNameTerm: { fontWeight: '700', color: colors.navy },
  tag: {
    fontSize: 12,
    fontWeight: '700',
    color: '#fff',
    backgroundColor: colors.gray,
    borderRadius: 5,
    paddingHorizontal: 7,
    paddingVertical: 2,
    overflow: 'hidden',
    marginLeft: 8,
  },
  tagStart: { backgroundColor: '#2DB400' },
  tagEnd: { backgroundColor: '#D32F2F' },
  hint: { fontSize: 13, color: colors.gray, marginTop: 8, marginLeft: 8 },
});
