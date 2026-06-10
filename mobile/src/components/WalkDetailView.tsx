/** 도보 상세 안내 — 상단 실시간 네비 지도(WalkNavMap) + Tmap 턴바이턴 리스트 + 행 탭 시 카카오 로드뷰 모달 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  Modal,
  ActivityIndicator,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { walkRouteDetail, type WalkGuide } from '../api/client';
import RoadView from './RoadView';
import WalkNavMap, { type NavCoord } from './WalkNavMap';
import { colors, sizes } from '../theme';

interface Props {
  kakaoKey: string;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  searchOption?: number; // 4=계단 회피(휠체어)
  /** 실시간 내 위치 — 있으면 상단에 네비게이션 지도 표시 */
  myPos?: NavCoord | null;
  /** 네비 지도 도착 라벨 (정류장/역 이름) */
  endLabel?: string;
}

/** Tmap turnType → 방향 아이콘 */
function turnIcon(t: number, desc: string): string {
  if (t === 200) return '🚩';
  if (t === 201) return '🏁';
  if (t === 11) return '↑';
  if (t === 12) return '↰';
  if (t === 13) return '↱';
  if (t === 14) return '⤺';
  if ([16, 17, 18].includes(t)) return '↰';
  if ([19, 20, 21].includes(t)) return '↱';
  // 횡단보도/육교/지하보도/계단/엘리베이터 등 보행시설
  if (t >= 125 && t <= 129) return '🚶';
  if (t >= 211 && t <= 217) return '🚶';
  // description 키워드 fallback
  if (desc.includes('좌회전') || desc.includes('왼쪽')) return '↰';
  if (desc.includes('우회전') || desc.includes('오른쪽')) return '↱';
  if (desc.includes('횡단보도')) return '🚶';
  return '↑';
}

/** 설명 텍스트 보정 (빈 값이면 turnType 기반 기본 문구) */
function guideText(g: WalkGuide): string {
  if (g.description) return g.description;
  if (g.turn_type === 200) return '출발';
  if (g.turn_type === 201) return '도착';
  if (g.turn_type === 11) return '직진';
  if (g.turn_type === 12) return '왼쪽 방향';
  if (g.turn_type === 13) return '오른쪽 방향';
  return '이동';
}

export default function WalkDetailView({
  kakaoKey,
  startLat,
  startLng,
  endLat,
  endLng,
  searchOption = 0,
  myPos = null,
  endLabel,
}: Props) {
  const [guides, setGuides] = useState<WalkGuide[] | null>(null);
  const [coords, setCoords] = useState<NavCoord[]>([]);
  const [rv, setRv] = useState<{ lat: number; lng: number; label: string } | null>(null);
  const { height: winH } = useWindowDimensions();

  useEffect(() => {
    let on = true;
    setGuides(null);
    setCoords([]);
    walkRouteDetail({
      start_x: startLng,
      start_y: startLat,
      end_x: endLng,
      end_y: endLat,
      search_option: searchOption,
    }).then((res) => {
      if (on) {
        setGuides(res.guides);
        setCoords(res.coords ?? []);
      }
    });
    return () => {
      on = false;
    };
  }, [startLat, startLng, endLat, endLng, searchOption]);

  if (guides === null) {
    return (
      <View style={styles.loadBox}>
        <ActivityIndicator color={colors.primary} />
        <Text style={styles.loadText}>도보 상세 경로 불러오는 중…</Text>
      </View>
    );
  }
  if (guides.length === 0) {
    return <Text style={styles.empty}>상세 도보 안내를 불러오지 못했습니다.</Text>;
  }

  return (
    <View style={styles.wrap}>
      {/* 실시간 네비게이션 지도 (경로선 + 내 위치 추적) */}
      {coords.length > 1 && (
        <WalkNavMap
          kakaoKey={kakaoKey}
          coords={coords}
          myPos={myPos}
          endLat={endLat}
          endLng={endLng}
          endLabel={endLabel}
          height={280}
        />
      )}
      <Text style={styles.title}>🚶 도보 상세 안내</Text>
      {guides.map((g, i) => {
        const isEnd = g.turn_type === 201;
        return (
          <Pressable
            key={i}
            style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
            onPress={() => setRv({ lat: g.lat, lng: g.lng, label: guideText(g) })}
            accessibilityRole="button"
            accessibilityLabel={`${guideText(g)}, 거리뷰 보기`}
          >
            <Text style={styles.icon}>{turnIcon(g.turn_type, g.description)}</Text>
            <View style={styles.rowMid}>
              <Text style={styles.desc}>{guideText(g)}</Text>
              {!isEnd && g.distance > 0 && (
                <Text style={styles.dist}>{g.distance}m 이동</Text>
              )}
            </View>
            <Text style={styles.rvHint}>거리뷰 ›</Text>
          </Pressable>
        );
      })}

      {/* 로드뷰 모달 */}
      <Modal
        visible={!!rv}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setRv(null)}
      >
        <View style={styles.modalRoot}>
          <View style={styles.modalHead}>
            <Text style={styles.modalTitle} numberOfLines={1}>
              📍 {rv?.label}
            </Text>
            <Pressable
              onPress={() => setRv(null)}
              hitSlop={10}
              accessibilityRole="button"
              accessibilityLabel="닫기"
            >
              <Text style={styles.modalClose}>✕ 닫기</Text>
            </Pressable>
          </View>
          {rv && (
            <RoadView
              kakaoKey={kakaoKey}
              lat={rv.lat}
              lng={rv.lng}
              height={Math.max(winH - 120, 300)}
            />
          )}
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: 8 },
  title: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.navy, marginBottom: 8 },
  loadBox: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14 },
  loadText: { color: colors.gray, fontSize: sizes.fontSmall },
  empty: { color: colors.gray, fontSize: sizes.fontSmall, padding: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
    marginBottom: 8,
  },
  rowPressed: { backgroundColor: colors.light },
  icon: { fontSize: 24, width: 36, textAlign: 'center', color: colors.navy },
  rowMid: { flex: 1, marginLeft: 6 },
  desc: { fontSize: sizes.fontSmall, color: colors.darkText, fontWeight: '600' },
  dist: { fontSize: 13, color: colors.gray, marginTop: 2 },
  rvHint: { fontSize: 13, color: colors.primary, fontWeight: '700', marginLeft: 8 },
  modalRoot: { flex: 1, backgroundColor: '#000' },
  modalHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: '#111',
  },
  modalTitle: { flex: 1, color: '#fff', fontSize: 16, fontWeight: '700', marginRight: 12 },
  modalClose: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
