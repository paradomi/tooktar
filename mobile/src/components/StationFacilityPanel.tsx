/** 교통약자 시설 패널 — pages/2_경로_상세.py 의 _render_station_panel 이식 (출구/방면 선택형) */
import React, { useState, useMemo, useEffect } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, sizes } from '../theme';
import ZoomableDiagram from './ZoomableDiagram';

interface Props {
  name: string; // 표시용 역명 (예: "망포")
  movement: any[]; // KRIC 이동경로 raw 배열
  recommendedExit?: string; // 추천 출구 "7번" (있으면 그 출구 자동선택)
  roleLabel?: string; // "승차역"/"하차역"/"환승역" 배지
  collapsible?: boolean; // 헤더 탭으로 접고 펼치기
  defaultOpen?: boolean; // collapsible 일 때 초기 펼침 여부
}

interface PathTuple {
  mgNo: string;
  items: any[];
  edPath: string;
}

interface ExitOption {
  label: string; // 원본 출구 라벨 ("3번 출입구")
  display: string; // 표시 라벨 ("✓ 3번 출입구 (추천)")
  paths: PathTuple[];
}

function firstNum(s: string): number {
  const m = s.match(/\d+/);
  return m ? parseInt(m[0], 10) : 999;
}

function roleColor(role?: string): string {
  if (role === '승차역') return '#2DB400';
  if (role === '하차역') return '#D32F2F';
  return '#1f77b4'; // 환승역
}

export default function StationFacilityPanel({
  name,
  movement,
  recommendedExit,
  roleLabel,
  collapsible = false,
  defaultOpen = true,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  // 1~4) 그룹화 + 출구별 묶기 + 추천 출구 자동선택 계산
  const { exitOptions, defaultExitLabel } = useMemo(() => {
    const groups: Record<string, any[]> = {};
    for (const item of movement || []) {
      const mg = String(item?.mvPathMgNo ?? 0);
      (groups[mg] = groups[mg] || []).push(item);
    }

    // 출구 라벨별로 묶기
    const exitGroups: Record<string, PathTuple[]> = {};
    for (const mgNo of Object.keys(groups)) {
      const items = [...groups[mgNo]].sort(
        (a, b) => (Number(a?.exitMvTpOrdr) || 0) - (Number(b?.exitMvTpOrdr) || 0),
      );
      const first = items[0] || {};
      const stPath: string = first.stMovePath || '';
      const edPath: string = first.edMovePath || '';

      const exitNums = (stPath.match(/(\d+)번/g) || []).map((x) => x.replace('번', ''));
      let exitLabel: string;
      if (exitNums.length === 1) exitLabel = `${exitNums[0]}번 출입구`;
      else if (exitNums.length > 1) exitLabel = `${exitNums.join(',')}번 출입구`;
      else exitLabel = stPath ? stPath.slice(0, 30) : `경로 ${mgNo}`;

      (exitGroups[exitLabel] = exitGroups[exitLabel] || []).push({ mgNo, items, edPath });
    }

    // 출구 옵션 정렬 (첫 숫자 오름차순)
    const sortedLabels = Object.keys(exitGroups).sort((a, b) => firstNum(a) - firstNum(b));

    // 추천 출구 매칭
    let defaultIdx = 0;
    let matched = false;
    if (recommendedExit) {
      const prefMatch = recommendedExit.match(/\d+/);
      if (prefMatch) {
        const prefN = prefMatch[0];
        for (let i = 0; i < sortedLabels.length; i++) {
          const numsInOpt: string[] = sortedLabels[i].match(/\d+/g) || [];
          if (numsInOpt.includes(prefN)) {
            defaultIdx = i;
            matched = true;
            break;
          }
        }
      }
    }

    const options: ExitOption[] = sortedLabels.map((label, i) => {
      let display = label;
      if (i === defaultIdx) {
        display = matched ? `✓ ${label} (추천)` : `✓ ${label}`;
      }
      return { label, display, paths: exitGroups[label] };
    });

    return {
      exitOptions: options,
      defaultExitLabel: options.length ? options[defaultIdx].label : '',
    };
  }, [movement, recommendedExit]);

  const [selectedExitLabel, setSelectedExitLabel] = useState(defaultExitLabel);
  const [selectedDirIdx, setSelectedDirIdx] = useState(0);
  const [exitOpen, setExitOpen] = useState(false);
  const [dirOpen, setDirOpen] = useState(false);

  // 추천/기본 출구가 바뀌면 동기화
  useEffect(() => {
    setSelectedExitLabel(defaultExitLabel);
  }, [defaultExitLabel]);

  // 출구가 바뀌면 방면 선택 초기화
  useEffect(() => {
    setSelectedDirIdx(0);
  }, [selectedExitLabel]);

  const currentExit =
    exitOptions.find((o) => o.label === selectedExitLabel) || exitOptions[0];

  // 8) 그룹 없음
  if (!currentExit) {
    return (
      <View style={styles.card}>
        <View style={styles.headerRow}>
          {!!roleLabel && (
            <View style={[styles.roleBadge, { backgroundColor: roleColor(roleLabel) }]}>
              <Text style={styles.roleBadgeText}>{roleLabel}</Text>
            </View>
          )}
          <Text style={styles.stationName}>🚇 {name}</Text>
        </View>
        <Text style={styles.muted}>이 역의 이동 경로 정보가 없습니다.</Text>
      </View>
    );
  }

  const paths = currentExit.paths;
  const hasDir = paths.length > 1;
  const dirIdx = hasDir ? Math.min(selectedDirIdx, paths.length - 1) : 0;
  const chosen = paths[dirIdx];
  const first = chosen.items[0] || {};
  const stPath: string = first.stMovePath || '';
  const imgHttps: string = first.imgPath
    ? String(first.imgPath).replace('http://', 'https://')
    : '';

  const dirLabel = (p: PathTuple, i: number) =>
    i === 0 ? `✓ ${p.edPath}` : p.edPath;

  const header = (
    <View style={styles.headerRow}>
      {!!roleLabel && (
        <View style={[styles.roleBadge, { backgroundColor: roleColor(roleLabel) }]}>
          <Text style={styles.roleBadgeText}>{roleLabel}</Text>
        </View>
      )}
      <Text style={styles.stationName}>🚇 {name}</Text>
      {collapsible && <Text style={styles.toggleIcon}>{open ? '▾' : '▸'}</Text>}
    </View>
  );

  return (
    <View style={styles.card}>
      {collapsible ? (
        <Pressable
          onPress={() => setOpen((v) => !v)}
          accessibilityRole="button"
          accessibilityLabel={`${name} ${roleLabel ?? ''} 시설 정보 ${open ? '접기' : '펼치기'}`}
        >
          {header}
        </Pressable>
      ) : (
        header
      )}

      {(!collapsible || open) && (
        <>
      {/* 출구 선택 */}
      <Text style={styles.pickerLabel}>이용할 출입구 선택</Text>
      <Pressable style={styles.pickerHead} onPress={() => setExitOpen((v) => !v)}>
        <Text style={styles.pickerHeadText} numberOfLines={1}>
          {currentExit.display}
        </Text>
        <Text style={styles.affordance}>▾</Text>
      </Pressable>
      {exitOpen && (
        <View style={styles.dropdown}>
          {exitOptions.map((opt) => (
            <Pressable
              key={opt.label}
              style={styles.option}
              onPress={() => {
                setSelectedExitLabel(opt.label);
                setSelectedDirIdx(0);
                setExitOpen(false);
              }}
            >
              <Text
                style={[
                  styles.optionText,
                  opt.label === currentExit.label && styles.optionTextSel,
                ]}
              >
                {opt.display}
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {/* 방면 선택 */}
      {hasDir && (
        <>
          <Text style={styles.pickerLabel}>방면 선택</Text>
          <Pressable style={styles.pickerHead} onPress={() => setDirOpen((v) => !v)}>
            <Text style={styles.pickerHeadText} numberOfLines={1}>
              {dirLabel(paths[dirIdx], dirIdx)}
            </Text>
            <Text style={styles.affordance}>▾</Text>
          </Pressable>
          {dirOpen && (
            <View style={styles.dropdown}>
              {paths.map((p, i) => (
                <Pressable
                  key={`${p.mgNo}-${i}`}
                  style={styles.option}
                  onPress={() => {
                    setSelectedDirIdx(i);
                    setDirOpen(false);
                  }}
                >
                  <Text style={[styles.optionText, i === dirIdx && styles.optionTextSel]}>
                    {dirLabel(p, i)}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}
        </>
      )}

      {/* 선택된 경로 헤더 */}
      <View style={styles.headerBox}>
        <Text style={styles.headerText}>
          🛣️ {stPath} → {chosen.edPath}
        </Text>
      </View>

      {/* 도면 이미지 — 탭하면 전체화면 핀치 확대 */}
      {!!imgHttps && (
        <View style={styles.imgWrap}>
          <ZoomableDiagram uri={imgHttps} height={360} />
        </View>
      )}

      {/* 이동 경로 설명 */}
      {chosen.items.map((it, i) =>
        it?.mvContDtl ? (
          <Text key={`desc-${i}`} style={styles.descLine}>
            {it.mvContDtl}
          </Text>
        ) : null,
      )}
        </>
      )}
    </View>
  );
}

const NAVY = '#002F6C';

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: sizes.radius,
    padding: 14,
    marginBottom: 8,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  roleBadge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginRight: 8,
  },
  roleBadgeText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  toggleIcon: { fontSize: sizes.fontBody, color: colors.gray, marginLeft: 8 },
  stationName: {
    flex: 1,
    fontSize: sizes.fontBody,
    fontWeight: '700',
    color: colors.navy,
  },
  muted: { fontSize: sizes.fontSmall, color: colors.grayLight },
  pickerLabel: {
    fontSize: 13,
    color: colors.gray,
    marginTop: 10,
    marginBottom: 4,
  },
  pickerHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.light,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  pickerHeadText: { flex: 1, fontSize: sizes.fontSmall, color: colors.darkText },
  affordance: { fontSize: sizes.fontSmall, color: colors.gray, marginLeft: 8 },
  dropdown: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    marginTop: 4,
    overflow: 'hidden',
  },
  option: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  optionText: { fontSize: sizes.fontSmall, color: colors.darkText },
  optionTextSel: { fontWeight: '700', color: colors.navy },
  headerBox: {
    marginTop: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: 'rgba(0,47,108,0.06)',
    borderLeftWidth: 4,
    borderLeftColor: NAVY,
    borderRadius: 8,
  },
  headerText: { fontSize: sizes.fontSmall, fontWeight: '700', color: NAVY },
  imgWrap: {
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#fff',
  },
  descLine: {
    marginTop: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    fontSize: 13,
    color: '#333',
  },
});
