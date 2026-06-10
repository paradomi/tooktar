/** 경로 탐색 화면 — pages/1_경로_탐색.py 이식
 *  모드 카드 + /routes/search 호출 + 경로 카드 리스트
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, sizes } from '../theme';
import { ROUTE_MODES, type RouteMode } from '../data/modes';
import ModeCard from '../components/ModeCard';
import RouteCard from '../components/RouteCard';
import {
  searchRoutes,
  scoreLowFloor,
  busArrivals,
  stationCodes,
  nextTrains,
  subwayDirection,
  type Route,
  type LowFloorScore,
} from '../api/client';
import type { RootStackParamList } from '../navigation/types';

interface ArrivalInfo {
  route: string;
  minutes: number;
  stopsLeft?: string | null;
  lowFloor?: boolean;
  place?: string; // 타는 곳 (정류장/역)
  direction?: string; // 방면
}

/** 경로의 첫 대중교통(버스/지하철) 다음 도착 안내 (구조화) */
async function firstTransitArrival(route: Route): Promise<ArrivalInfo | null> {
  const first = (route.steps ?? []).find((s) => s.type === 'bus' || s.type === 'subway');
  if (!first) return null;
  if (first.type === 'bus' && first.bus_no) {
    const arr = await busArrivals({
      station_id: first.start_id,
      lng: first.start_x,
      lat: first.start_y,
      station_name: first.start_name,
    });
    const m = arr.find((a) => a.route_name === first.bus_no);
    const p = m?.predictions?.[0];
    if (p?.minutes != null) {
      return {
        route: `${first.bus_no}번`,
        minutes: p.minutes,
        stopsLeft: p.stops_left ? `${p.stops_left}정류장 전` : null,
        lowFloor: p.low_floor,
        place: first.start_name || undefined,
        direction: first.end_name ? `${first.end_name} 방면` : undefined,
      };
    }
    return null;
  }
  if (first.type === 'subway' && first.start_name) {
    // 출발·도착역 코드 조회를 병렬로 (순차 대비 절반 시간)
    const [codes, endCodes] = await Promise.all([
      stationCodes(first.start_name, first.line_name ?? ''),
      first.end_name
        ? stationCodes(first.end_name, first.line_name ?? '')
        : Promise.resolve(null),
    ]);
    if (!codes) return null;
    const res = await nextTrains({
      rail_op_cd: codes.rail_op_cd,
      ln_cd: codes.ln_cd,
      stin_cd: codes.stin_cd,
      to_stin_cd: endCodes?.stin_cd,
      limit: 1,
    });
    const t = res.trains?.[0];
    if (t) {
      const dir = await subwayDirection(
        first.start_name,
        first.end_name ?? '',
        first.line_name ?? ''
      );
      return {
        route: first.line_name ?? '지하철',
        minutes: t.minutes_until,
        place: first.start_name || undefined,
        direction: dir || undefined,
      };
    }
  }
  return null;
}

type Props = NativeStackScreenProps<RootStackParamList, 'Routes'>;

export default function RoutesScreen({ route, navigation }: Props) {
  const { origin, dest } = route.params;
  const [mode, setMode] = useState<RouteMode['key']>('fast');
  const [routes, setRoutes] = useState<Route[]>([]);
  const [scores, setScores] = useState<Record<number, LowFloorScore>>({});
  const [arrivals, setArrivals] = useState<Record<number, ArrivalInfo>>({});
  const [loading, setLoading] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchType = useMemo(
    () => ROUTE_MODES.find((m) => m.key === mode)?.searchType ?? 0,
    [mode]
  );
  const modeDesc = useMemo(
    () => ROUTE_MODES.find((m) => m.key === mode)?.desc ?? '',
    [mode]
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await searchRoutes({
        origin_lng: origin.lng,
        origin_lat: origin.lat,
        dest_lng: dest.lng,
        dest_lat: dest.lat,
        search_type: searchType,
      });
      let list = res.routes;
      if (mode === 'walk_less') {
        list = [...list].sort(
          (a, b) => a.transfers - b.transfers || a.total_walk - b.total_walk
        );
      }
      setRoutes(list);
      setScores({});
      setArrivals({});
      if (list.length === 0) {
        setError('경로를 찾지 못했습니다. 출발지·도착지를 확인해주세요.');
        return;
      }

      // 휠체어 모드: 저상버스 친화도 점수로 정렬 (tier 우선 → 시간 → 도보)
      // 속도를 위해 시간 빠른 상위 N개만 저상 검증 (나머지는 미확인 tier 2)
      let finalList = list;
      const scoreMap: Record<number, LowFloorScore> = {}; // 콜백 재정렬에서도 참조
      if (mode === 'wheel') {
        setScoring(true);
        const SCORE_TOP_N = 6;
        const byTime = [...list].sort((a, b) => a.total_minutes - b.total_minutes);
        const toScore = byTime.slice(0, SCORE_TOP_N);
        const sc = await scoreLowFloor(toScore);
        sc.forEach((s) => (scoreMap[s.id] = s));
        setScores(scoreMap);
        const tierOf = (r: Route) => scoreMap[r.id]?.tier ?? 2; // 미점수화 = 미확인(2)
        const sorted = byTime.sort(
          (a, b) =>
            tierOf(a) - tierOf(b) ||
            a.total_minutes - b.total_minutes ||
            a.total_walk - b.total_walk
        );
        setRoutes(sorted);
        setScoring(false);
        finalList = sorted;
      }

      // 상위 N개 경로의 첫 대중교통 도착시간 조회.
      // ⚠️ Promise.all 로 묶으면 가장 느린 1개(특히 지하철 다단계 조회) 때문에 빠른 버스 도착도
      //    늦게 뜸 → 각 경로가 끝나는 즉시 개별 반영(점진적), 재정렬은 전부 끝난 뒤 한 번.
      const ARR_TOP_N = 6;
      const ARR_SOON_MIN = 30;
      const top = finalList.slice(0, ARR_TOP_N);
      const amap: Record<number, ArrivalInfo> = {};
      const tasks = top.map((r) =>
        firstTransitArrival(r)
          .then((info) => {
            if (info) {
              amap[r.id] = info;
              setArrivals((prev) => ({ ...prev, [r.id]: info })); // 도착하는 대로 즉시 표시
            }
          })
          .catch(() => {}) // 한 경로 실패가 다른 경로를 막지 않도록
      );

      Promise.allSettled(tasks).then(() => {
        // 30분 내 도착 여부로 그룹 분리(0=곧 옴, 1=늦거나 미확인). 기존 정렬은 그룹 내에서 유지.
        const soonGroup = (r: Route) => {
          const a = amap[r.id];
          return a && a.minutes <= ARR_SOON_MIN ? 0 : 1;
        };
        const tierOf = (r: Route) =>
          mode === 'wheel' ? scoreMap[r.id]?.tier ?? 2 : 0;
        const reSorted = [...finalList].sort((a, b) => {
          // 휠체어는 저상 tier 우선 유지 → 그 안에서 도착 임박 우선
          const t = tierOf(a) - tierOf(b);
          if (t !== 0) return t;
          const g = soonGroup(a) - soonGroup(b);
          if (g !== 0) return g;
          return a.total_minutes - b.total_minutes || a.total_walk - b.total_walk;
        });
        setRoutes(reSorted);
      });
    } catch (e) {
      setError('경로 검색에 실패했습니다. 백엔드 연결을 확인해주세요.');
      setRoutes([]);
    } finally {
      setLoading(false);
    }
  }, [origin, dest, searchType, mode]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="dark" />

      {/* 헤더 */}
      <View style={styles.header}>
        <Pressable
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          accessibilityRole="button"
          accessibilityLabel="뒤로"
        >
          <Text style={styles.backText}>‹ 뒤로</Text>
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {dest.name}
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* 출발 → 도착 요약 */}
        <View style={styles.odRow}>
          <Text style={styles.odText} numberOfLines={1}>
            📍 {origin.name}
          </Text>
          <Text style={styles.odArrow}>↓</Text>
          <Text style={styles.odText} numberOfLines={1}>
            🏁 {dest.name}
          </Text>
        </View>

        {/* 모드 카드 */}
        <View style={styles.modeRow}>
          {ROUTE_MODES.map((m) => (
            <View key={m.key} style={styles.modeItem}>
              <ModeCard mode={m} selected={mode === m.key} onPress={setMode} />
            </View>
          ))}
        </View>
        <View style={styles.descBox}>
          <Text style={styles.descText}>{modeDesc}</Text>
        </View>

        {/* 결과 */}
        {loading && (
          <View style={styles.center}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={styles.loadingText}>경로를 찾는 중...</Text>
          </View>
        )}

        {!loading && error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
            <Pressable style={styles.retryBtn} onPress={load}>
              <Text style={styles.retryText}>다시 시도</Text>
            </Pressable>
          </View>
        )}

        {!loading && !error && mode === 'wheel' && scoring && (
          <View style={styles.scoringRow}>
            <ActivityIndicator color={colors.primary} />
            <Text style={styles.scoringText}>저상버스 운행 확인 중...</Text>
          </View>
        )}

        {!loading &&
          !error &&
          routes.map((r, i) => (
            <RouteCard
              key={r.id}
              route={r}
              rank={i + 1}
              lowFloorScore={mode === 'wheel' ? scores[r.id]?.score : undefined}
              arrival={arrivals[r.id]}
              onPress={(selected) =>
                navigation.navigate('Detail', { route: selected, origin, dest, mode })
              }
            />
          ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  backBtn: { minHeight: sizes.minTouch, justifyContent: 'center', paddingRight: 12 },
  backText: { fontSize: 18, color: colors.primary, fontWeight: '700' },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: '700', color: colors.navy },
  scroll: { padding: 16, paddingBottom: 40 },
  odRow: {
    backgroundColor: colors.card,
    borderRadius: sizes.radiusSm,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 16,
    alignItems: 'center',
  },
  odText: { fontSize: sizes.fontBody, color: colors.darkText, fontWeight: '600' },
  odArrow: { fontSize: 18, color: colors.grayLight, marginVertical: 2 },
  modeRow: { flexDirection: 'row', marginHorizontal: -4 },
  modeItem: { flex: 1, paddingHorizontal: 4 },
  descBox: {
    backgroundColor: colors.light,
    borderRadius: sizes.radiusSm,
    padding: 12,
    marginTop: 10,
    marginBottom: 16,
  },
  descText: { fontSize: sizes.fontSmall, color: colors.navy },
  scoringRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  scoringText: { marginLeft: 8, color: colors.gray, fontSize: sizes.fontSmall },
  center: { alignItems: 'center', paddingVertical: 40 },
  loadingText: { marginTop: 12, color: colors.gray, fontSize: sizes.fontBody },
  errorBox: { alignItems: 'center', paddingVertical: 30 },
  errorText: { color: colors.gray, fontSize: sizes.fontBody, textAlign: 'center', marginBottom: 16 },
  retryBtn: {
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    paddingHorizontal: 24,
    height: sizes.minTouch,
    justifyContent: 'center',
  },
  retryText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
});
