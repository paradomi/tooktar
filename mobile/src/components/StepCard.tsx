/** 경로 단계 카드 — pages/2_경로_상세.py 의 단계별 안내 이식 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, sizes } from '../theme';
import type { RouteStep } from '../api/client';

interface Props {
  step: RouteStep;
  isTransferWalk?: boolean;
  children?: React.ReactNode; // 실시간 도착 정보 등
  direction?: string; // 지하철 방면 라벨 "(종점, 인접역) 방면"
  inExit?: string; // 진입 출구 "7번"
  outExit?: string; // 하차 출구 "10번"
}

function meta(step: RouteStep) {
  switch (step.type) {
    case 'bus':
      return { icon: '🚌', color: colors.blue };
    case 'subway':
      return { icon: '🚇', color: '#2DB400' };
    case 'walk':
      return { icon: '🚶', color: '#FF8C00' };
    default:
      return { icon: '•', color: colors.gray };
  }
}

export default function StepCard({
  step,
  isTransferWalk,
  children,
  direction,
  inExit,
  outExit,
}: Props) {
  const m = meta(step);
  const borderColor = isTransferWalk ? '#7B1FA2' : m.color;

  // 헤드 라인
  let head = '';
  if (step.type === 'bus') head = `${step.bus_no ?? ''}번 버스`;
  else if (step.type === 'subway') head = step.line_name ?? '지하철';
  else head = step.desc ?? '도보';

  const showOD = step.type === 'bus' || step.type === 'subway';
  const unit = step.type === 'subway' ? '역' : '정거장';

  return (
    <View style={[styles.card, { borderLeftColor: borderColor }]}>
      <Text style={styles.head}>
        {m.icon} {head}
      </Text>

      {/* 지하철 방면 */}
      {!!direction && <Text style={styles.direction}>↗ {direction}</Text>}

      {showOD && (
        <View style={styles.odRow}>
          <Text style={styles.odSub}>승차</Text>
          <Text style={styles.odName}>{step.start_name}</Text>
          <Text style={styles.odArrow}>→</Text>
          <Text style={styles.odSub}>하차</Text>
          <Text style={styles.odName}>{step.end_name}</Text>
        </View>
      )}

      {/* 진입/하차 출구 */}
      {(!!inExit || !!outExit) && (
        <View style={styles.exitBox}>
          {!!inExit && (
            <Text style={styles.exitText}>
              🚪 <Text style={styles.exitBold}>{inExit} 출구</Text>로 진입
            </Text>
          )}
          {!!outExit && (
            <Text style={styles.exitText}>
              🚪 <Text style={styles.exitBold}>{outExit} 출구</Text>로 나가기
            </Text>
          )}
        </View>
      )}

      {children}

      {showOD && (step.station_count ?? 0) > 0 && (
        <Text style={styles.metaLine}>
          {step.station_count}{unit} · {step.section_time}분 이동
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#F8F9FA',
    borderLeftWidth: 5,
    borderRadius: sizes.radiusSm,
    paddingVertical: 14,
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  head: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.darkText },
  direction: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.navy, marginTop: 6 },
  exitBox: {
    backgroundColor: 'rgba(45,180,0,0.08)',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 8,
  },
  exitText: { fontSize: sizes.fontSmall, color: colors.darkText, marginVertical: 1 },
  exitBold: { fontWeight: '700', color: colors.navy },
  odRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', marginTop: 8 },
  odSub: { fontSize: 13, color: colors.gray, marginRight: 4 },
  odName: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.navy, marginRight: 8 },
  odArrow: { color: colors.grayLight, marginRight: 8 },
  metaLine: { fontSize: 13, color: colors.gray, marginTop: 8 },
});
