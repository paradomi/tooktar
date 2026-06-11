/** 경로 상세 화면 — pages/2_경로_상세.py 이식 (지도 제외)
 *  단계별 안내 + 버스/지하철 실시간 도착 + AI 브리핑
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import * as Speech from 'expo-speech';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, sizes } from '../theme';
import StepCard from '../components/StepCard';
import RouteMap from '../components/RouteMap';
import StationFacilityPanel from '../components/StationFacilityPanel';
import { getCurrentCoord } from '../utils/location';
import {
  busArrivals,
  busLowFloor,
  stationCodes,
  nextTrains,
  subwayFacilities,
  getBriefing,
  getNarrative,
  diagramAnalysis,
  getConfig,
  loadLane,
  walkRoute,
  subwayDirection,
  subwayExits,
  transitColor,
  type RouteStep,
  type NextTrain,
  type LaneData,
  type TransferCtx,
} from '../api/client';
import type { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Detail'>;

interface BusInfo {
  predictions: { minutes?: number; lowFloor?: boolean; stopsLeft?: string | null }[];
  lowFloorOnRoute: boolean;
}
interface SubInfo {
  trains: NextTrain[];
  lastDpt: string | null;
  status: string;
}
interface StationFacility {
  name: string; // 표시용 역명(full_name)
  rawName: string; // step의 역명 (출구 추천 매칭용)
  movement: any[]; // KRIC 이동경로 raw
  recommendedExit?: string; // 추천 출구 "7번" (subwayExitMap 기반)
  role: '승차역' | '하차역' | '환승역'; // 여정 내 역할
}

export default function DetailScreen({ route, navigation }: Props) {
  const { route: r, origin, dest, mode } = route.params;
  const steps = r.steps ?? [];

  // 환승 지점: transit↔transit 사이 도보의 끝점(없으면 다음 transit 시작). 지도 🔄 마커용.
  const transferPoints = useMemo(() => {
    const pts: { lat: number; lng: number }[] = [];
    steps.forEach((s, i) => {
      if (s.type !== 'walk') return;
      const prev = steps[i - 1];
      const next = steps[i + 1];
      const isTransfer =
        prev &&
        ['bus', 'subway'].includes(prev.type) &&
        next &&
        ['bus', 'subway'].includes(next.type);
      if (!isTransfer) return;
      const lng = s.end_x ?? next?.start_x;
      const lat = s.end_y ?? next?.start_y;
      if (lat && lng) pts.push({ lat, lng });
    });
    return pts;
  }, [steps]);

  // 대중교통 구간(도보 제외) — lane 폴리라인 순서와 1:1 대응. 색상·라벨용.
  const transitSteps = useMemo(
    () => steps.filter((s) => s.type === 'bus' || s.type === 'subway'),
    [steps]
  );
  // 색상 정밀화 (지하철=파랑/일반=초록/광역=빨강/마을=노랑)
  const transit = useMemo(
    () =>
      transitSteps.map((s) => ({
        kind: (s.type === 'subway' ? 'subway' : 'bus') as 'bus' | 'subway',
        busType: s.bus_type,
      })),
    [transitSteps]
  );
  // 노선 라벨 마커: 구간 중간 지점에 "5번"/"수인분당선" 표시
  const transitLabels = useMemo(
    () =>
      transitSteps
        .map((s) => {
          const lat =
            s.start_y != null && s.end_y != null
              ? (s.start_y + s.end_y) / 2
              : s.start_y ?? s.end_y;
          const lng =
            s.start_x != null && s.end_x != null
              ? (s.start_x + s.end_x) / 2
              : s.start_x ?? s.end_x;
          if (lat == null || lng == null) return null;
          const isBus = s.type === 'bus';
          const label = isBus
            ? `🚌 ${s.bus_no ?? ''}`.trim()
            : `🚇 ${s.line_name ?? '지하철'}`.trim();
          return {
            lat,
            lng,
            label,
            color: transitColor(isBus ? 'bus' : 'subway', s.bus_type),
          };
        })
        .filter((x): x is NonNullable<typeof x> => x !== null),
    [transitSteps]
  );

  const [busMap, setBusMap] = useState<Record<number, BusInfo>>({});
  const [subMap, setSubMap] = useState<Record<number, SubInfo>>({});
  const [briefing, setBriefing] = useState<string>('');
  const [narrative, setNarrative] = useState<string>(''); // AI 여정 예행연습 + 환승 집중
  const [loadingNarrative, setLoadingNarrative] = useState(true);
  const [loadingArrivals, setLoadingArrivals] = useState(true);
  const [loadingBriefing, setLoadingBriefing] = useState(true);
  const [kakaoKey, setKakaoKey] = useState<string>('');
  const [lane, setLane] = useState<LaneData | null>(null);
  const [myLocation, setMyLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [walkLines, setWalkLines] = useState<{ lat: number; lng: number }[][]>([]);
  // 지하철 step별 방면 라벨 (step index → "(종점, 인접역) 방면")
  const [directions, setDirections] = useState<Record<number, string>>({});
  // 역명 → {in, out} 출구
  const [subwayExitMap, setSubwayExitMap] = useState<
    Record<string, { in?: string; out?: string }>
  >({});
  const [facilities, setFacilities] = useState<StationFacility[]>([]);
  const [loadingFac, setLoadingFac] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  // 음성 안내(TTS) 토글
  const toggleSpeech = useCallback(() => {
    if (speaking) {
      Speech.stop();
      setSpeaking(false);
      return;
    }
    const text = toSpeech([narrative, briefing].filter(Boolean).join('\n\n'));
    if (!text) return;
    setSpeaking(true);
    Speech.speak(text, {
      language: 'ko-KR',
      rate: 0.95,
      onDone: () => setSpeaking(false),
      onStopped: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    });
  }, [speaking, briefing, narrative]);

  // 화면 떠날 때 음성 정지
  useEffect(() => {
    return () => {
      Speech.stop();
    };
  }, []);

  // 지도: 카카오 키 + lane 폴리라인 + 도보경로 + 현재 위치 로드
  const loadMap = useCallback(async () => {
    const cfg = await getConfig();
    setKakaoKey(cfg.kakao_js_key);
    if (r.map_obj) {
      const ld = await loadLane(r.map_obj);
      setLane(ld);
    }
    // 도보 구간(Tmap 보행경로) — ODsay lane엔 도보 좌표가 없어 별도 호출.
    // ODsay 도보 step은 한쪽 끝점만 줄 때가 많음 → 빠진 끝점을
    // 인접 transit step / 출발·도착지 좌표로 보완한다.
    const opt = mode === 'wheel' ? 4 : 0; // 휠체어=계단 회피
    const steps = r.steps ?? [];
    const walkJobs: { sx: number; sy: number; ex: number; ey: number }[] = [];
    steps.forEach((s, i) => {
      if (s.type !== 'walk') return;
      let sx = s.start_x;
      let sy = s.start_y;
      let ex = s.end_x;
      let ey = s.end_y;
      // start 보완: 이전 transit의 끝점 → 없으면 출발지
      if (!sx || !sy) {
        for (let j = i - 1; j >= 0; j--) {
          if (steps[j].end_x && steps[j].end_y) { sx = steps[j].end_x; sy = steps[j].end_y; break; }
        }
        if (!sx || !sy) { sx = origin.lng; sy = origin.lat; }
      }
      // end 보완: 다음 transit의 시작점 → 없으면 도착지
      if (!ex || !ey) {
        for (let j = i + 1; j < steps.length; j++) {
          if (steps[j].start_x && steps[j].start_y) { ex = steps[j].start_x; ey = steps[j].start_y; break; }
        }
        if (!ex || !ey) { ex = dest.lng; ey = dest.lat; }
      }
      if (sx && sy && ex && ey) {
        walkJobs.push({ sx, sy, ex, ey });
      }
    });
    if (walkJobs.length) {
      const lines = await Promise.all(
        walkJobs.map((w) =>
          walkRoute({ start_x: w.sx, start_y: w.sy, end_x: w.ex, end_y: w.ey, search_option: opt })
        )
      );
      setWalkLines(lines.filter((l) => l.length > 1));
    }
    // 현재 위치(GPS) — 파란 점 마커용
    const c = await getCurrentCoord();
    if (c) setMyLocation(c);
  }, [r.map_obj, r.steps, mode]);

  // 지하철 방면 + 진입/하차 출구 로드
  const loadSubwayInfo = useCallback(async () => {
    const steps2 = r.steps ?? [];
    // 방면: 지하철 step마다
    const dirEntries = await Promise.all(
      steps2.map(async (s, idx) => {
        if (s.type !== 'subway' || !s.start_name || !s.end_name) return null;
        const label = await subwayDirection(s.start_name, s.end_name, s.line_name ?? '');
        return [idx, label] as const;
      })
    );
    const dirMap: Record<number, string> = {};
    dirEntries.forEach((e) => {
      if (e) dirMap[e[0]] = e[1];
    });
    setDirections(dirMap);
    // 출구: 전체 step 흐름으로 한 번에 (휠체어면 접근가능 출구로 제한)
    const ex = await subwayExits(steps2, origin, dest, mode === 'wheel');
    setSubwayExitMap(ex);
  }, [r.steps, origin, dest, mode]);

  // 실시간 도착 정보 로드 (버스 + 지하철)
  const loadArrivals = useCallback(async () => {
    setLoadingArrivals(true);
    const bMap: Record<number, BusInfo> = {};
    const sMap: Record<number, SubInfo> = {};
    await Promise.all(
      steps.map(async (s, idx) => {
        if (s.type === 'bus' && s.bus_no) {
          const arrivals = await busArrivals({
            station_id: s.start_id,
            lng: s.start_x,
            lat: s.start_y,
            station_name: s.start_name,
          });
          const matched = arrivals.find((a) => a.route_name === s.bus_no);
          const preds = (matched?.predictions ?? []).slice(0, 2).map((p) => ({
            minutes: p.minutes,
            lowFloor: p.low_floor,
            stopsLeft: p.stops_left,
          }));
          const anyLow = preds.some((p) => p.lowFloor);
          // 첫 도착에 저상 없으면 노선 단위 검증
          const lowOnRoute = anyLow || (await busLowFloor(s.bus_no, s.start_id));
          bMap[idx] = { predictions: preds, lowFloorOnRoute: lowOnRoute };
        } else if (s.type === 'subway' && s.start_name) {
          const codes = await stationCodes(s.start_name, s.line_name ?? '');
          if (codes) {
            const endCodes = s.end_name
              ? await stationCodes(s.end_name, s.line_name ?? '')
              : null;
            const res = await nextTrains({
              rail_op_cd: codes.rail_op_cd,
              ln_cd: codes.ln_cd,
              stin_cd: codes.stin_cd,
              to_stin_cd: endCodes?.stin_cd,
              limit: 2,
            });
            sMap[idx] = { trains: res.trains, lastDpt: res.last_dpt, status: res.status };
          }
        }
      })
    );
    setBusMap(bMap);
    setSubMap(sMap);
    setLoadingArrivals(false);
  }, [steps]);

  // 지하철 교통약자 시설 로드 (역명 dedup, 여정 순서 보존: 승차역 → 환승역 → 하차역)
  const loadFacilities = useCallback(async () => {
    const names: { name: string; line: string }[] = [];
    const seen = new Set<string>();
    for (const s of steps) {
      if (s.type !== 'subway') continue;
      for (const nm of [s.start_name, s.end_name]) {
        if (nm && !seen.has(nm)) {
          seen.add(nm);
          names.push({ name: nm, line: s.line_name ?? '' });
        }
      }
    }
    if (names.length === 0) return;
    setLoadingFac(true);

    // 역할: 첫 역=승차, 마지막 역=하차, 중간=환승
    const roleOf = (i: number): StationFacility['role'] =>
      i === 0 ? '승차역' : i === names.length - 1 ? '하차역' : '환승역';

    // ⚠️ Promise.all + push 는 완료 순서대로 들어가 여정 순서가 깨짐 → 인덱스로 자리 고정
    const slots: (StationFacility | null)[] = new Array(names.length).fill(null);
    await Promise.all(
      names.map(async ({ name, line }, i) => {
        const codes = await stationCodes(name, line);
        if (!codes) return;
        const fac = await subwayFacilities({
          rail_op_cd: codes.rail_op_cd,
          ln_cd: codes.ln_cd,
          stin_cd: codes.stin_cd,
        });
        slots[i] = {
          name: codes.full_name || name,
          rawName: name,
          movement: fac.movement || [],
          role: roleOf(i),
        };
      })
    );
    setFacilities(slots.filter((x): x is StationFacility => x !== null));
    setLoadingFac(false);
  }, [steps]);

  // AI 브리핑 로드
  const loadBriefing = useCallback(async () => {
    setLoadingBriefing(true);
    // 휠체어 모드: 첫 지하철역 도면을 Gemini Vision으로 분석해 브리핑에 추가
    let diagram = '';
    if (mode === 'wheel') {
      const firstSub = (r.steps ?? []).find(
        (s) => s.type === 'subway' && s.start_name
      );
      if (firstSub?.start_name) {
        const codes = await stationCodes(firstSub.start_name, firstSub.line_name ?? '');
        if (codes) {
          const fac = await subwayFacilities({
            rail_op_cd: codes.rail_op_cd,
            ln_cd: codes.ln_cd,
            stin_cd: codes.stin_cd,
          });
          const imgUrl = (fac.movement || []).find((m: any) => m?.imgPath)?.imgPath;
          if (imgUrl) {
            const dir = firstSub.end_name ? `${firstSub.end_name} 방면` : '';
            diagram = await diagramAnalysis(imgUrl, firstSub.start_name, dir);
          }
        }
      }
    }
    const text = await getBriefing({
      route: r,
      mode,
      origin_name: origin.name,
      dest_name: dest.name,
      diagram_insight: diagram || null,
    });
    setBriefing(text);
    setLoadingBriefing(false);
  }, [r, mode, origin, dest]);

  useEffect(() => {
    loadArrivals();
    loadBriefing();
    loadMap();
    loadFacilities();
    loadSubwayInfo();
  }, [loadArrivals, loadBriefing, loadMap, loadFacilities, loadSubwayInfo]);

  // AI 여정 내러티브: 도착정보·시설 로드가 끝나면 환승 컨텍스트를 모아 1회 생성
  const narrativeRequested = useRef(false);
  useEffect(() => {
    if (narrativeRequested.current) return;
    if (loadingArrivals || loadingFac) return;
    narrativeRequested.current = true;

    const transfers: TransferCtx[] = [];
    steps.forEach((s, i) => {
      if (s.type !== 'walk') return;
      const prev = steps[i - 1];
      const next = steps[i + 1];
      if (!prev || !next) return;
      if (!['bus', 'subway'].includes(prev.type) || !['bus', 'subway'].includes(next.type))
        return;
      const alight =
        prev.type === 'bus'
          ? `${prev.end_name ?? ''} 정류장 (${prev.bus_no ?? ''}번 버스 하차)`
          : `${prev.end_name ?? ''}역 (${prev.line_name ?? '지하철'} 하차)`;
      const board =
        next.type === 'bus'
          ? `${next.start_name ?? ''} 정류장에서 ${next.bus_no ?? ''}번 버스`
          : `${next.start_name ?? ''}역에서 ${next.line_name ?? '지하철'}`;
      // KRIC 역내 이동경로 요약 (하차/승차 역 이름 매칭)
      const names = [prev.end_name, next.start_name].filter(Boolean) as string[];
      const fac = facilities.find((f) =>
        names.some((n) => f.rawName.includes(n) || n.includes(f.rawName))
      );
      const facility = fac
        ? fac.movement
            .slice(0, 3)
            .map((m: any) => m?.mvContDtl || m?.stMovePath || '')
            .filter(Boolean)
            .join(' / ')
        : '';
      // 다음 버스 도착·저상 정보
      let arrival = '';
      if (next.type === 'bus') {
        const b = busMap[i + 1];
        const p = b?.predictions?.[0];
        if (p?.minutes != null)
          arrival = `${p.minutes}분 후 도착${
            p.lowFloor ? ' (저상버스)' : b?.lowFloorOnRoute ? ' (노선 저상 운행)' : ''
          }`;
      }
      transfers.push({ alight, board, facility, arrival, walk: s.desc ?? '' });
    });

    getNarrative({ route: r, mode, origin_name: origin.name, dest_name: dest.name, transfers })
      .then(setNarrative)
      .finally(() => setLoadingNarrative(false));
  }, [loadingArrivals, loadingFac, steps, facilities, busMap, r, mode, origin, dest]);

  const isTransferWalk = (idx: number) => {
    const s = steps[idx];
    if (s.type !== 'walk') return false;
    const prev = steps[idx - 1];
    const next = steps[idx + 1];
    return (
      !!prev &&
      ['bus', 'subway'].includes(prev.type) &&
      !!next &&
      ['bus', 'subway'].includes(next.type)
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>‹ 뒤로</Text>
        </Pressable>
        <Text style={styles.headerTitle}>{r.total_minutes}분 · 경로 안내</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* 지도 */}
        <Text style={styles.sectionTitle}>🗺️ 경로 지도</Text>
        <RouteMap
          kakaoKey={kakaoKey}
          lane={lane}
          origin={origin}
          dest={dest}
          myLocation={myLocation}
          walkLines={walkLines}
          transferPoints={transferPoints}
          transit={transit}
          transitLabels={transitLabels}
          height={280}
        />

        {/* 요약 */}
        <View style={styles.summaryBox}>
          <Text style={styles.summaryTitle}>
            {r.total_minutes}분 · {r.summary}
          </Text>
          <Text style={styles.summaryMeta}>
            환승 {r.transfers}회 · 도보 {r.total_walk}m · {r.payment.toLocaleString()}원
          </Text>
        </View>

        {/* 안내 모드 시작 */}
        <Pressable
          style={({ pressed }) => [styles.guideBtn, pressed && { opacity: 0.85 }]}
          onPress={() => navigation.navigate('Guide', { route: r, origin, dest, mode })}
          accessibilityRole="button"
          accessibilityLabel="안내 시작"
        >
          <Text style={styles.guideBtnText}>🧭 안내 시작</Text>
        </Pressable>

        {/* 단계별 안내 */}
        <Text style={styles.sectionTitle}>📋 단계별 안내</Text>
        {loadingArrivals && (
          <View style={styles.inlineLoad}>
            <ActivityIndicator color={colors.primary} />
            <Text style={styles.inlineLoadText}>실시간 도착 정보 확인 중...</Text>
          </View>
        )}
        {steps.map((s, idx) => (
          <StepCard
            key={idx}
            step={s}
            isTransferWalk={isTransferWalk(idx)}
            direction={s.type === 'subway' ? directions[idx] : undefined}
            inExit={s.type === 'subway' ? subwayExitMap[s.start_name ?? '']?.in : undefined}
            outExit={s.type === 'subway' ? subwayExitMap[s.end_name ?? '']?.out : undefined}
          >
            <ArrivalInfo step={s} bus={busMap[idx]} sub={subMap[idx]} />
          </StepCard>
        ))}

        {/* 교통약자 시설 */}
        {(loadingFac || facilities.length > 0) && (
          <>
            <Text style={styles.sectionTitle}>♿ 교통약자 시설 정보</Text>
            {loadingFac && (
              <View style={styles.inlineLoad}>
                <ActivityIndicator color={colors.primary} />
                <Text style={styles.inlineLoadText}>역 시설 정보 확인 중...</Text>
              </View>
            )}
            {facilities.map((f, i) => (
              <StationFacilityPanel
                key={i}
                name={f.name}
                movement={f.movement}
                roleLabel={f.role}
                collapsible={facilities.length > 1}
                defaultOpen={facilities.length === 1 || f.role === '승차역'}
                recommendedExit={
                  f.role === '하차역'
                    ? subwayExitMap[f.rawName]?.out || subwayExitMap[f.rawName]?.in
                    : subwayExitMap[f.rawName]?.in || subwayExitMap[f.rawName]?.out
                }
              />
            ))}
          </>
        )}

        {/* AI 브리핑 */}
        <View style={styles.briefingHeader}>
          <Text style={styles.sectionTitle}>🤖 AI 경로 브리핑</Text>
          {!loadingBriefing && !!briefing && (
            <Pressable
              style={[styles.speakBtn, speaking && styles.speakBtnActive]}
              onPress={toggleSpeech}
              accessibilityRole="button"
              accessibilityLabel={speaking ? '음성 안내 정지' : '음성 안내 듣기'}
            >
              <Text style={[styles.speakText, speaking && styles.speakTextActive]}>
                {speaking ? '■ 정지' : '🔊 듣기'}
              </Text>
            </Pressable>
          )}
        </View>
        {/* AI 여정 미리보기 (예행연습 + 환승 집중 안내) */}
        {(loadingNarrative || !!narrative) && (
          <View style={styles.narrativeBox}>
            {loadingNarrative ? (
              <View style={styles.narrativeLoading}>
                <ActivityIndicator color={colors.navy} size="small" />
                <Text style={styles.narrativeLoadingText}>AI가 여정을 미리 살펴보는 중…</Text>
              </View>
            ) : (
              <>
                <Text style={styles.narrativeTitle}>🧭 여정 미리보기</Text>
                <Text style={styles.narrativeText}>{stripMd(narrative)}</Text>
              </>
            )}
          </View>
        )}
        <View style={styles.briefingBox}>
          {loadingBriefing ? (
            <ActivityIndicator color={colors.primary} />
          ) : (
            <Text style={styles.briefingText}>{stripMd(briefing)}</Text>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

/** step 카드 내부 실시간 도착 표시 */
function ArrivalInfo({
  step,
  bus,
  sub,
}: {
  step: RouteStep;
  bus?: BusInfo;
  sub?: SubInfo;
}) {
  if (step.type === 'bus' && bus) {
    return (
      <View style={styles.arrival}>
        {bus.lowFloorOnRoute && (
          <View style={styles.lowChip}>
            <Text style={styles.lowChipText}>♿ 저상 운행</Text>
          </View>
        )}
        {bus.predictions.length > 0 ? (
          <Text style={styles.arrivalText}>
            ⏱️{' '}
            {bus.predictions
              .map(
                (p) =>
                  `${p.minutes}분 후${p.lowFloor ? ' ♿' : ''}${
                    p.stopsLeft ? ` (${p.stopsLeft}정류장 전)` : ''
                  }`
              )
              .join(' · ')}
          </Text>
        ) : (
          <Text style={styles.arrivalMuted}>⏱️ 도착 정보 없음</Text>
        )}
      </View>
    );
  }

  if (step.type === 'subway' && sub) {
    if (sub.status === 'ok' && sub.trains.length > 0) {
      return (
        <View style={styles.arrival}>
          <Text style={styles.arrivalText}>
            ⏱️{' '}
            {sub.trains
              .map((t) => `${t.minutes_until}분 후 (${t.destination}행)`)
              .join(' · ')}
            {sub.lastDpt ? ` · 막차 ${sub.lastDpt}` : ''}
          </Text>
        </View>
      );
    }
    if (sub.status === 'after_last') {
      return (
        <View style={styles.arrival}>
          <Text style={styles.arrivalMuted}>
            ⏱️ 오늘 운행 종료{sub.lastDpt ? ` (막차 ${sub.lastDpt})` : ''}
          </Text>
        </View>
      );
    }
    return (
      <View style={styles.arrival}>
        <Text style={styles.arrivalMuted}>⏱️ 도착 정보 없음</Text>
      </View>
    );
  }

  return null;
}

/** 간단 마크다운 제거 (**bold** → bold) */
function stripMd(s: string): string {
  return s.replace(/\*\*(.*?)\*\*/g, '$1');
}

/** 음성 안내용 텍스트: 마크다운 + 이모지/픽토그램 제거 (TTS가 이모지 이름 읽는 것 방지) */
function toSpeech(s: string): string {
  return stripMd(s)
    // 이모지·기호 영역 제거 (그림문자, 기호, 교통/지도 픽토그램, 여러 변형선택자 포함)
    .replace(
      /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{FE00}-\u{FE0F}\u{200D}\u{20E3}\u{2122}\u{2139}]/gu,
      ''
    )
    .replace(/[ \t]{2,}/g, ' ') // 이모지 자리에 남은 중복 공백 정리
    .replace(/^[ \t]+/gm, '') // 줄 앞 공백 제거
    .trim();
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
  summaryBox: {
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    marginBottom: 16,
  },
  summaryTitle: { fontSize: 22, fontWeight: '800', color: colors.navy },
  summaryMeta: { fontSize: sizes.fontSmall, color: colors.gray, marginTop: 6 },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.navy,
    marginTop: 16,
    marginBottom: 12,
  },
  inlineLoad: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  inlineLoadText: { marginLeft: 8, color: colors.gray, fontSize: sizes.fontSmall },
  arrival: {
    backgroundColor: 'rgba(0,47,108,0.06)',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 8,
  },
  arrivalText: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.navy },
  arrivalMuted: { fontSize: sizes.fontSmall, color: colors.grayLight },
  lowChip: {
    alignSelf: 'flex-start',
    backgroundColor: colors.lowFloor,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 3,
    marginBottom: 6,
  },
  lowChipText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  guideBtn: {
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch + 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  guideBtnText: { color: '#fff', fontSize: 20, fontWeight: '800' },
  briefingHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  speakBtn: {
    minHeight: 40,
    paddingHorizontal: 16,
    borderRadius: sizes.radiusSm,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  speakBtnActive: { backgroundColor: colors.danger },
  speakText: { color: '#fff', fontSize: sizes.fontSmall, fontWeight: '700' },
  speakTextActive: { color: '#fff' },
  briefingBox: {
    backgroundColor: '#F3E5F5',
    borderRadius: sizes.radius,
    padding: 16,
    minHeight: 60,
  },
  briefingText: { fontSize: sizes.fontBody, color: colors.darkText, lineHeight: 28 },
  narrativeBox: {
    backgroundColor: '#EAF3FC',
    borderRadius: sizes.radius,
    borderWidth: 1.5,
    borderColor: '#BBD7F0',
    padding: 16,
    marginBottom: 10,
  },
  narrativeLoading: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  narrativeLoadingText: { fontSize: sizes.fontSmall, color: colors.navy, fontWeight: '600' },
  narrativeTitle: {
    fontSize: sizes.fontBody,
    fontWeight: '800',
    color: colors.navy,
    marginBottom: 8,
  },
  narrativeText: { fontSize: sizes.fontBody, color: colors.darkText, lineHeight: 28 },
});
