/** 경로 결과 카드 — components/route_card.py 이식 (요약본) */
import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { colors, sizes } from '../theme';
import type { Route } from '../api/client';

interface Props {
  route: Route;
  rank: number;
  onPress?: (route: Route) => void;
  /** 휠체어 모드 저상 점수: 1=확정, 0~1=부분, 0=없음, null=미확인, 'subway_only'=지하철 */
  lowFloorScore?: number | null | 'subway_only';
  /** 첫 대중교통 도착 안내 (구조화) */
  arrival?: {
    route: string; // "20-2번" / "수인분당선"
    minutes: number; // 도착까지 분 (0이면 곧 도착)
    stopsLeft?: string | null; // "3정류장 전"
    lowFloor?: boolean; // 저상버스
    place?: string; // 타는 곳 (정류장/역)
    direction?: string; // 방면
  };
}

/** 저상 점수 → 배지 텍스트/색 */
function lfBadge(score: number | null | 'subway_only'): { text: string; color: string } | null {
  if (score === 'subway_only') return { text: '지하철 경로', color: '#2DB400' };
  if (score === 1) return { text: '♿ 저상 확보', color: '#002F6C' };
  if (typeof score === 'number' && score > 0) return { text: '♿ 일부 저상', color: '#1f77b4' };
  if (score === 0) return { text: '저상 없음', color: '#8A98A6' };
  return null; // null = 미확인
}

/** 경로 step → 구간 막대 세그먼트 (카카오맵 이동시간 표시줄) */
interface Segment {
  type: string;
  minutes: number;
  color: string;
  label: string; // 막대 위 표기
}
function buildSegments(route: Route): Segment[] {
  const segs: Segment[] = [];
  for (const s of route.steps ?? []) {
    let minutes = s.section_time ?? 0;
    if (s.type === 'walk') {
      // 도보 분: section_time 없으면 desc에서 추출 시도
      if (!minutes) {
        const m = (s.desc ?? '').match(/(\d+)\s*분/);
        minutes = m ? parseInt(m[1], 10) : 0;
      }
      segs.push({ type: 'walk', minutes, color: '#B7C0CC', label: `${minutes || ''}` });
    } else if (s.type === 'bus') {
      segs.push({ type: 'bus', minutes, color: '#2DB400', label: `${minutes}` });
    } else if (s.type === 'subway') {
      segs.push({ type: 'subway', minutes, color: '#1f77b4', label: `${minutes}` });
    }
  }
  return segs.filter((s) => s.type !== 'walk' || s.minutes > 0);
}

/** path_type: 1=지하철, 2=버스, 3=버스+지하철 */
function typeChip(pathType: number): { label: string; color: string } {
  switch (pathType) {
    case 1:
      return { label: '지하철', color: '#2DB400' };
    case 2:
      return { label: '버스', color: colors.blue };
    case 3:
      return { label: '버스+지하철', color: colors.navy };
    default:
      return { label: '대중교통', color: colors.gray };
  }
}

/** 세그먼트 타입 → 아이콘 */
function segIcon(type: string): string {
  if (type === 'bus') return '🚌';
  if (type === 'subway') return '🚇';
  return '🚶';
}

export default function RouteCard({ route, rank, onPress, lowFloorScore, arrival }: Props) {
  const chip = typeChip(route.path_type);
  // 점수 배지. 단, 실시간 도착이 '저상'이면 점수가 0/미확인이어도 모순이므로 '저상 확보'로 보정.
  let lf = lowFloorScore !== undefined ? lfBadge(lowFloorScore) : null;
  if (arrival?.lowFloor && (lowFloorScore === 0 || lowFloorScore == null)) {
    lf = { text: '♿ 저상 확보', color: '#002F6C' };
  }
  const segments = buildSegments(route);
  // 막대 폭 비례 계산 (최소 폭 보장)
  const totalMin = segments.reduce((a, s) => a + Math.max(s.minutes, 1), 0) || 1;

  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
      onPress={() => onPress?.(route)}
      accessibilityRole="button"
      accessibilityLabel={`${route.total_minutes}분 경로, 상세 보기`}
    >
      <View style={styles.topRow}>
        <View style={[styles.chip, { backgroundColor: chip.color }]}>
          <Text style={styles.chipText}>{chip.label}</Text>
        </View>
        {rank === 1 && (
          <View style={styles.bestChip}>
            <Text style={styles.bestText}>추천</Text>
          </View>
        )}
        <Text style={styles.time}>{route.total_minutes}분</Text>
      </View>

      <Text style={styles.summary}>{route.summary}</Text>

      <View style={styles.metaRow}>
        <Text style={styles.meta}>환승 {route.transfers}회</Text>
        <Text style={styles.metaDot}>·</Text>
        <Text style={styles.meta}>도보 {route.total_walk}m</Text>
        <Text style={styles.metaDot}>·</Text>
        <Text style={styles.meta}>{route.payment.toLocaleString()}원</Text>
      </View>

      {/* 구간 이동시간 표시줄 (도보·버스·지하철) */}
      {segments.length > 0 && (
        <View style={styles.segBar}>
          {segments.map((s, i) => (
            <View
              key={i}
              style={[
                styles.seg,
                { flex: Math.max(s.minutes, 1) / totalMin, backgroundColor: s.color },
                i === 0 && styles.segFirst,
                i === segments.length - 1 && styles.segLast,
              ]}
            >
              <Text style={styles.segText} numberOfLines={1}>
                {segIcon(s.type)} {s.minutes}분
              </Text>
            </View>
          ))}
        </View>
      )}

      {!!arrival && (!!arrival.place || !!arrival.direction) && (
        <View style={styles.placeRow}>
          {!!arrival.place && (
            <Text style={styles.placeText} numberOfLines={1}>
              🚏 {arrival.place}
            </Text>
          )}
          {!!arrival.direction && (
            <Text style={styles.dirText} numberOfLines={1}>
              {arrival.direction}
            </Text>
          )}
        </View>
      )}

      {!!arrival && (
        <View style={styles.arrivalRow}>
          <Text style={styles.arrRoute}>{arrival.route}</Text>
          {arrival.minutes <= 1 ? (
            <Text style={styles.arrSoon}>곧 도착</Text>
          ) : (
            <Text style={styles.arrMin}>{arrival.minutes}분</Text>
          )}
          {!!arrival.stopsLeft && <Text style={styles.arrStops}>{arrival.stopsLeft}</Text>}
          {arrival.lowFloor && (
            <View style={styles.lowFloorChip}>
              <Text style={styles.lowFloorChipText}>♿ 저상</Text>
            </View>
          )}
        </View>
      )}

      {lf && (
        <View style={[styles.lfBadge, { backgroundColor: lf.color }]}>
          <Text style={styles.lfText}>{lf.text}</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#1F3A5E',
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  pressed: { backgroundColor: colors.light, transform: [{ scale: 0.99 }] },
  topRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  chip: { borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  chipText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  bestChip: {
    marginLeft: 8,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: colors.teal,
  },
  bestText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  time: { marginLeft: 'auto', fontSize: 24, fontWeight: '800', color: colors.navy },
  summary: { fontSize: sizes.fontBody, color: colors.darkText, marginBottom: 8 },
  metaRow: { flexDirection: 'row', alignItems: 'center' },
  meta: { fontSize: sizes.fontSmall, color: colors.gray },
  metaDot: { color: colors.grayLight, marginHorizontal: 6 },
  segBar: {
    flexDirection: 'row',
    alignItems: 'stretch',
    marginTop: 12,
    height: 30,
    borderRadius: 15,
    overflow: 'hidden',
  },
  seg: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
    marginRight: 2,
  },
  segFirst: { borderTopLeftRadius: 15, borderBottomLeftRadius: 15 },
  segLast: { borderTopRightRadius: 15, borderBottomRightRadius: 15, marginRight: 0 },
  segText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  placeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: 12,
    gap: 8,
  },
  placeText: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.navy },
  dirText: { fontSize: sizes.fontSmall, color: colors.blue, fontWeight: '600' },
  arrivalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: 6,
    gap: 8,
  },
  arrRoute: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.darkText },
  arrMin: { fontSize: sizes.fontBody + 4, fontWeight: '800', color: '#E8590C' }, // 주황
  arrSoon: { fontSize: sizes.fontBody + 2, fontWeight: '800', color: '#E03131' }, // 빨강
  arrStops: { fontSize: sizes.fontSmall, color: colors.gray },
  lowFloorChip: {
    borderWidth: 1.5,
    borderColor: '#2DB400',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  lowFloorChipText: { fontSize: 13, fontWeight: '700', color: '#2DB400' },
  lfBadge: {
    alignSelf: 'flex-start',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 10,
  },
  lfText: { color: '#fff', fontSize: 13, fontWeight: '700' },
});
