/** 안내 모드 — 포그라운드 실시간 GPS 기반 단계별 안내.
 *  도보 네비게이션(남은 거리/방향) + 승차/하차 근접 알람(화면 + 진동).
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, Pressable, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import * as Haptics from 'expo-haptics';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, sizes } from '../theme';
import { watchPosition, distanceM } from '../utils/location';
import { getConfig, transitColor, type RouteStep } from '../api/client';
import WalkDetailView from '../components/WalkDetailView';
import TransitProgressView from '../components/TransitProgressView';
import type { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Guide'>;

// 근접 판정 반경(m)
const ARRIVE_RADIUS = 60; // 정류장/역/목적지 도착으로 간주
const ALERT_RADIUS = 150; // "곧 도착/하차" 알람 시작

interface GuideStep {
  idx: number;
  step: RouteStep;
  targetLat: number; // 이 step의 도착 지점 (다음 행동이 일어나는 곳)
  targetLng: number;
  startLat?: number; // 도보 시작점 (도보 상세 안내용)
  startLng?: number;
  kind: 'walk' | 'board' | 'alight'; // 도보 / 승차 / 하차
  title: string;
  sub: string;
}

/** route.steps → 안내용 step 리스트 (좌표 보완) */
function buildGuideSteps(
  steps: RouteStep[],
  origin: { lat: number; lng: number },
  dest: { lat: number; lng: number }
): GuideStep[] {
  const out: GuideStep[] = [];
  steps.forEach((s, i) => {
    if (s.type === 'walk') {
      // 도보의 끝점 = 다음 정류장/역 또는 목적지
      let ex = s.end_x;
      let ey = s.end_y;
      if (!ex || !ey) {
        for (let j = i + 1; j < steps.length; j++) {
          if (steps[j].start_x && steps[j].start_y) {
            ex = steps[j].start_x;
            ey = steps[j].start_y;
            break;
          }
        }
        if (!ex || !ey) {
          ex = dest.lng;
          ey = dest.lat;
        }
      }
      const next = steps[i + 1];
      const toName = next?.start_name || (i === steps.length - 1 ? '목적지' : '');
      // 도보 시작점: step.start → 이전 step end → 출발지
      let sx = s.start_x;
      let sy = s.start_y;
      if (!sx || !sy) {
        for (let j = i - 1; j >= 0; j--) {
          if (steps[j].end_x && steps[j].end_y) {
            sx = steps[j].end_x;
            sy = steps[j].end_y;
            break;
          }
        }
      }
      if (!sx || !sy) {
        sx = origin.lng;
        sy = origin.lat;
      }
      out.push({
        idx: i,
        step: s,
        targetLat: ey as number,
        targetLng: ex as number,
        startLat: sy as number,
        startLng: sx as number,
        kind: 'walk',
        title: toName ? `${toName}까지 도보` : '도보 이동',
        sub: s.desc || '',
      });
    } else if (s.type === 'bus' || s.type === 'subway') {
      const ride =
        s.type === 'bus' ? `${s.bus_no ?? ''}번 버스` : s.line_name ?? '지하철';
      // 승차: 승차역 위치
      if (s.start_x && s.start_y) {
        out.push({
          idx: i,
          step: s,
          targetLat: s.start_y,
          targetLng: s.start_x,
          kind: 'board',
          title: `${s.start_name} 승차`,
          sub: `${ride} 탑승`,
        });
      }
      // 하차: 하차역 위치 (다음 step의 시작 or end 추정)
      let ax = s.end_x;
      let ay = s.end_y;
      if (!ax || !ay) {
        const nx = steps[i + 1];
        if (nx?.start_x && nx?.start_y) {
          ax = nx.start_x;
          ay = nx.start_y;
        }
      }
      if (ax && ay) {
        out.push({
          idx: i,
          step: s,
          targetLat: ay,
          targetLng: ax,
          kind: 'alight',
          title: `${s.end_name} 하차`,
          sub: `${ride} 하차 · ${s.station_count ?? ''}${s.type === 'subway' ? '역' : '정거장'}`,
        });
      }
    }
  });
  return out;
}

export default function GuideScreen({ route, navigation }: Props) {
  const { route: r, origin, dest, mode } = route.params;
  const guideSteps = useMemo(
    () => buildGuideSteps(r.steps ?? [], origin, dest),
    [r.steps, origin, dest]
  );

  const [stepIdx, setStepIdx] = useState(0);
  const [myPos, setMyPos] = useState<{ lat: number; lng: number } | null>(null);
  const [alerted, setAlerted] = useState(false); // 현재 step 알람 1회 발생 여부
  const [kakaoKey, setKakaoKey] = useState('');
  const stopRef = useRef<(() => void) | null>(null);

  // 카카오 키 (로드뷰용)
  useEffect(() => {
    getConfig()
      .then((c) => setKakaoKey(c.kakao_js_key || ''))
      .catch(() => {});
  }, []);

  const current = guideSteps[stepIdx];
  const distToTarget = useMemo(() => {
    if (!myPos || !current) return null;
    return Math.round(
      distanceM(myPos, { lat: current.targetLat, lng: current.targetLng })
    );
  }, [myPos, current]);

  const buzz = useCallback((heavy = false) => {
    if (Platform.OS === 'web') return;
    Haptics.notificationAsync(
      heavy
        ? Haptics.NotificationFeedbackType.Warning
        : Haptics.NotificationFeedbackType.Success
    ).catch(() => {});
  }, []);

  // 위치 추적 시작
  useEffect(() => {
    let mounted = true;
    watchPosition((c) => {
      if (mounted) setMyPos(c);
    }).then((stop) => {
      stopRef.current = stop;
    });
    return () => {
      mounted = false;
      stopRef.current?.();
    };
  }, []);

  // 근접 알람 (자동 단계 전환은 하지 않음 — 사용자가 버튼으로 직접 이동)
  useEffect(() => {
    if (distToTarget == null || !current) return;
    if (distToTarget <= ALERT_RADIUS && !alerted) {
      setAlerted(true);
      buzz(current.kind !== 'walk');
    }
  }, [distToTarget, current, alerted, buzz]);

  const isLast = stepIdx >= guideSteps.length - 1;
  const arrivedAll = isLast && distToTarget != null && distToTarget <= ARRIVE_RADIUS;

  const kindBadge = (k: GuideStep['kind']) =>
    k === 'walk'
      ? { txt: '도보', color: '#FF8C00' }
      : k === 'board'
      ? { txt: '승차', color: '#2DB400' }
      : { txt: '하차', color: colors.blue };

  // 알람 메시지
  let alertMsg = '';
  if (current && distToTarget != null) {
    if (current.kind === 'board' && distToTarget <= ALERT_RADIUS)
      alertMsg = '🔔 곧 승차 정류장입니다. 버스를 기다리세요.';
    else if (current.kind === 'alight' && distToTarget <= ALERT_RADIUS)
      alertMsg = '🔔 곧 하차할 곳입니다. 내릴 준비를 하세요.';
    else if (current.kind === 'walk' && distToTarget <= ARRIVE_RADIUS)
      alertMsg = '✅ 거의 도착했습니다.';
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>‹ 종료</Text>
        </Pressable>
        <Text style={styles.headerTitle}>🧭 안내 모드</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {arrivedAll ? (
          <View style={styles.doneBox}>
            <Text style={styles.doneEmoji}>🎉</Text>
            <Text style={styles.doneText}>목적지에 도착했습니다!</Text>
          </View>
        ) : current ? (
          <>
            {/* 현재 단계 큰 카드 */}
            <View style={styles.bigCard}>
              <View
                style={[styles.kindChip, { backgroundColor: kindBadge(current.kind).color }]}
              >
                <Text style={styles.kindChipText}>{kindBadge(current.kind).txt}</Text>
              </View>
              <Text style={styles.bigTitle}>{current.title}</Text>
              {!!current.sub && <Text style={styles.bigSub}>{current.sub}</Text>}

              {distToTarget != null ? (
                <Text style={styles.distText}>
                  남은 거리{' '}
                  <Text style={styles.distNum}>
                    {distToTarget >= 1000 ? (distToTarget / 1000).toFixed(1) : distToTarget}
                  </Text>{' '}
                  {distToTarget >= 1000 ? 'km' : 'm'}
                </Text>
              ) : (
                <Text style={styles.distMuted}>위치 확인 중…</Text>
              )}
            </View>

            {/* 알람 배너 */}
            {!!alertMsg && (
              <View style={styles.alertBox}>
                <Text style={styles.alertText}>{alertMsg}</Text>
              </View>
            )}

            {/* 도보 단계: 턴바이턴 상세 + 거리뷰 */}
            {current.kind === 'walk' &&
              current.startLat != null &&
              current.startLng != null && (
                <WalkDetailView
                  kakaoKey={kakaoKey}
                  startLat={current.startLat}
                  startLng={current.startLng}
                  endLat={current.targetLat}
                  endLng={current.targetLng}
                  searchOption={mode === 'wheel' ? 4 : 0}
                  myPos={myPos}
                  endLabel={current.title.replace(/까지 도보$/, '') || '도착'}
                />
              )}

            {/* 승하차 단계: 탑승→하차 정류장 진행 화면 (실시간 위치) */}
            {(current.kind === 'board' || current.kind === 'alight') &&
              (current.step.pass_stops?.length ?? 0) > 0 && (
                <TransitProgressView
                  stops={current.step.pass_stops!}
                  myPos={myPos}
                  kind={current.step.type === 'subway' ? 'subway' : 'bus'}
                  lineLabel={
                    current.step.type === 'subway'
                      ? current.step.line_name ?? '지하철'
                      : `${current.step.bus_no ?? ''}번 버스`
                  }
                  color={transitColor(
                    current.step.type === 'subway' ? 'subway' : 'bus',
                    current.step.bus_type
                  )}
                />
              )}

            {/* 단계 진행 표시 */}
            <Text style={styles.progress}>
              {stepIdx + 1} / {guideSteps.length} 단계
            </Text>

            {/* 다음 단계 미리보기 */}
            {guideSteps[stepIdx + 1] && (
              <View style={styles.nextBox}>
                <Text style={styles.nextLabel}>다음</Text>
                <Text style={styles.nextText}>{guideSteps[stepIdx + 1].title}</Text>
              </View>
            )}

            {/* 단계 이동 버튼 (이전 / 다음) */}
            <View style={styles.stepBtnRow}>
              <Pressable
                style={[styles.prevBtn, stepIdx === 0 && styles.btnDisabled]}
                disabled={stepIdx === 0}
                onPress={() => {
                  setStepIdx((v) => Math.max(v - 1, 0));
                  setAlerted(false);
                }}
                accessibilityRole="button"
                accessibilityLabel="이전 단계로"
              >
                <Text style={[styles.prevText, stepIdx === 0 && styles.btnTextDisabled]}>
                  ‹ 이전
                </Text>
              </Pressable>
              <Pressable
                style={[styles.manualBtn, isLast && styles.btnDisabled]}
                disabled={isLast}
                onPress={() => {
                  setStepIdx((v) => Math.min(v + 1, guideSteps.length - 1));
                  setAlerted(false);
                }}
                accessibilityRole="button"
                accessibilityLabel="다음 단계로"
              >
                <Text style={[styles.manualText, isLast && styles.btnTextDisabled]}>
                  다음 단계로 ›
                </Text>
              </Pressable>
            </View>
          </>
        ) : (
          <Text style={styles.distMuted}>안내할 경로 정보가 없습니다.</Text>
        )}
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
  backText: { fontSize: 18, color: colors.danger, fontWeight: '700' },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: '700', color: colors.navy },
  scroll: { padding: 18 },
  bigCard: {
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 24,
    alignItems: 'center',
  },
  kindChip: { borderRadius: 10, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 14 },
  kindChipText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  bigTitle: { fontSize: 26, fontWeight: '800', color: colors.navy, textAlign: 'center' },
  bigSub: { fontSize: sizes.fontBody, color: colors.gray, marginTop: 8, textAlign: 'center' },
  distText: { fontSize: sizes.fontBody, color: colors.darkText, marginTop: 20 },
  distNum: { fontSize: 40, fontWeight: '800', color: '#E8590C' },
  distMuted: { fontSize: sizes.fontBody, color: colors.grayLight, marginTop: 20 },
  alertBox: {
    backgroundColor: '#FFF3CD',
    borderRadius: sizes.radiusSm,
    padding: 16,
    marginTop: 16,
  },
  alertText: { fontSize: sizes.fontBody, fontWeight: '700', color: '#8A6D00', textAlign: 'center' },
  progress: { fontSize: sizes.fontSmall, color: colors.gray, textAlign: 'center', marginTop: 18 },
  nextBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.light,
    borderRadius: sizes.radiusSm,
    padding: 14,
    marginTop: 12,
    gap: 10,
  },
  nextLabel: { fontSize: sizes.fontSmall, color: colors.grayLight, fontWeight: '700' },
  nextText: { fontSize: sizes.fontBody, color: colors.navy, fontWeight: '700' },
  stepBtnRow: { flexDirection: 'row', gap: 10, marginTop: 20 },
  prevBtn: {
    flex: 1,
    backgroundColor: colors.card,
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch + 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  prevText: { color: colors.primary, fontSize: sizes.fontBody, fontWeight: '700' },
  manualBtn: {
    flex: 2,
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch + 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  manualText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
  btnDisabled: { opacity: 0.35 },
  btnTextDisabled: { color: colors.grayLight },
  doneBox: { alignItems: 'center', paddingVertical: 60 },
  doneEmoji: { fontSize: 64 },
  doneText: { fontSize: 24, fontWeight: '800', color: colors.navy, marginTop: 16 },
});
