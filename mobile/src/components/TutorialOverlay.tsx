/** 사용법 튜토리얼 오버레이 — 장소 추가부터 안내 모드까지 단계별 안내.
 *  단계 전환 시 페이드+슬라이드, 아이콘 두둥실(bounce) 애니메이션.
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  Modal,
  Animated,
  Easing,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { colors, sizes } from '../theme';

interface Props {
  visible: boolean;
  onClose: () => void;
}

interface Step {
  icon: string;
  title: string;
  lines: string[]; // 자연스러운 안내 문구 (줄 단위)
  mock?: React.ReactNode; // 화면 미니 미리보기 (선택)
}

/** 미니 UI 목업 조각들 — 실제 화면과 닮은 작은 예시 */
function MockFavCard() {
  return (
    <View style={m.row}>
      <View style={m.favCard}>
        <Text style={m.favIcon}>🏠</Text>
        <Text style={m.favLabel}>집</Text>
      </View>
      <View style={[m.favCard, m.favCardAdd]}>
        <Text style={m.favIcon}>➕</Text>
        <Text style={m.favLabel}>장소 추가</Text>
      </View>
    </View>
  );
}

function MockSearch() {
  return (
    <View style={m.searchBox}>
      <Text style={m.searchText}>🔍 수원시청</Text>
      <View style={m.searchBtn}>
        <Text style={m.searchBtnText}>경로 찾기</Text>
      </View>
    </View>
  );
}

function MockModes() {
  return (
    <View style={m.row}>
      <View style={m.mode}><Text style={m.modeIcon}>⚡</Text><Text style={m.modeText}>빠른 길</Text></View>
      <View style={[m.mode, m.modeOn]}><Text style={m.modeIcon}>♿</Text><Text style={[m.modeText, m.modeTextOn]}>휠체어 맞춤</Text></View>
      <View style={m.mode}><Text style={m.modeIcon}>🚶</Text><Text style={m.modeText}>덜 걷는 길</Text></View>
    </View>
  );
}

function MockRoute() {
  return (
    <View style={m.routeCard}>
      <Text style={m.routeTime}>42<Text style={m.routeMin}>분</Text></Text>
      <Text style={m.routeDesc}>🚌 13-1번 · ♿ 저상 8분 후 도착</Text>
    </View>
  );
}

function MockGuide() {
  return (
    <View style={m.guideCard}>
      <Text style={m.guideDist}>남은 거리 <Text style={m.guideNum}>120</Text> m</Text>
      <Text style={m.guideAlert}>🔔 곧 하차할 곳입니다</Text>
    </View>
  );
}

const STEPS: Step[] = [
  {
    icon: '👋',
    title: '툭 타에 오신 것을 환영해요',
    lines: [
      '교통약자를 위한 길찾기 앱이에요.',
      '저상버스, 엘리베이터, 계단 없는 길까지',
      '"탈 수 있는 경로"만 골라 알려드려요.',
      '사용법을 차근차근 알려드릴게요.',
    ],
  },
  {
    icon: '⭐',
    title: '1. 자주 가는 곳 등록하기',
    lines: [
      '홈의 「✏️ 편집」을 누르면',
      '집, 병원처럼 자주 가는 곳을',
      '➕ 버튼으로 등록할 수 있어요.',
      '다음부터는 카드 한 번만 누르면 바로 출발!',
    ],
    mock: <MockFavCard />,
  },
  {
    icon: '🔍',
    title: '2. 목적지 검색하기',
    lines: [
      '검색창에 가고 싶은 곳을 입력하면',
      '자동완성으로 장소가 떠요.',
      '고른 뒤 「경로 찾기」를 누르세요.',
    ],
    mock: <MockSearch />,
  },
  {
    icon: '♿',
    title: '3. 나에게 맞는 길 고르기',
    lines: [
      '빠른 길 · 휠체어 맞춤 · 덜 걷는 길,',
      '세 가지 중에서 고를 수 있어요.',
      '휠체어 맞춤을 고르면 저상버스가 곧 오는',
      '경로를 먼저 보여드려요.',
    ],
    mock: <MockModes />,
  },
  {
    icon: '🚌',
    title: '4. 경로 살펴보기',
    lines: [
      '경로 카드에는 걸리는 시간과 함께',
      '버스가 몇 분 뒤에 오는지,',
      '저상버스인지까지 표시돼요.',
      '카드를 누르면 지도와 단계별 안내,',
      '역 엘리베이터 위치까지 볼 수 있어요.',
    ],
    mock: <MockRoute />,
  },
  {
    icon: '🧭',
    title: '5. 안내 모드로 출발!',
    lines: [
      '경로 상세에서 「안내 시작」을 누르면',
      '내 위치를 따라 한 단계씩 안내하고,',
      '내릴 곳이 가까워지면 알려드려요.',
      '이제 직접 한번 해볼까요?',
    ],
    mock: <MockGuide />,
  },
];

export default function TutorialOverlay({ visible, onClose }: Props) {
  const [idx, setIdx] = useState(0);
  const fade = useRef(new Animated.Value(1)).current;
  const slide = useRef(new Animated.Value(0)).current;
  const bounce = useRef(new Animated.Value(0)).current;
  const { height: winH } = useWindowDimensions();

  // 열릴 때 첫 단계로
  useEffect(() => {
    if (visible) setIdx(0);
  }, [visible]);

  // 아이콘 두둥실 반복 애니메이션
  useEffect(() => {
    if (!visible) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(bounce, { toValue: -8, duration: 700, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
        Animated.timing(bounce, { toValue: 0, duration: 700, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [visible, bounce]);

  const go = (next: number) => {
    const dir = next > idx ? 1 : -1;
    // 현재 내용 페이드아웃+밀어내기 → 내용 교체 → 반대편에서 들어오기
    Animated.parallel([
      Animated.timing(fade, { toValue: 0, duration: 140, useNativeDriver: true }),
      Animated.timing(slide, { toValue: -28 * dir, duration: 140, useNativeDriver: true }),
    ]).start(() => {
      setIdx(next);
      slide.setValue(28 * dir);
      Animated.parallel([
        Animated.timing(fade, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.timing(slide, { toValue: 0, duration: 200, easing: Easing.out(Easing.quad), useNativeDriver: true }),
      ]).start();
    });
  };

  const step = STEPS[idx];
  const isLast = idx === STEPS.length - 1;

  return (
    // animationType 사용 금지: RN-web 에서 닫힘 애니메이션 이벤트가 누락되면 모달이 안 닫힘
    <Modal visible={visible} animationType="none" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={[styles.card, { maxHeight: winH - 80 }]}>
          {/* 건너뛰기 */}
          <Pressable
            style={styles.skip}
            onPress={onClose}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel="튜토리얼 건너뛰기"
          >
            <Text style={styles.skipText}>건너뛰기 ✕</Text>
          </Pressable>

          {/* 내용 (애니메이션) */}
          <Animated.View
            style={[styles.body, { opacity: fade, transform: [{ translateX: slide }] }]}
          >
            <Animated.Text style={[styles.icon, { transform: [{ translateY: bounce }] }]}>
              {step.icon}
            </Animated.Text>
            <Text style={styles.title}>{step.title}</Text>
            {step.lines.map((l, i) => (
              <Text key={i} style={styles.line}>
                {l}
              </Text>
            ))}
            {step.mock && <View style={styles.mockWrap}>{step.mock}</View>}
          </Animated.View>

          {/* 진행 점 */}
          <View style={styles.dots}>
            {STEPS.map((_, i) => (
              <View key={i} style={[styles.dot, i === idx && styles.dotOn]} />
            ))}
          </View>

          {/* 이전/다음 */}
          <View style={styles.btnRow}>
            <Pressable
              style={[styles.prevBtn, idx === 0 && styles.btnHidden]}
              disabled={idx === 0}
              onPress={() => go(idx - 1)}
              accessibilityRole="button"
              accessibilityLabel="이전 단계"
            >
              <Text style={styles.prevText}>‹ 이전</Text>
            </Pressable>
            <Pressable
              style={styles.nextBtn}
              onPress={() => (isLast ? onClose() : go(idx + 1))}
              accessibilityRole="button"
              accessibilityLabel={isLast ? '튜토리얼 마치기' : '다음 단계'}
            >
              <Text style={styles.nextText}>{isLast ? '시작하기 🚀' : '다음 ›'}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,18,40,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  card: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#fff',
    borderRadius: 20,
    paddingTop: 18,
    paddingBottom: 20,
    paddingHorizontal: 22,
  },
  skip: { alignSelf: 'flex-end', minHeight: 36, justifyContent: 'center' },
  skipText: { color: colors.grayLight, fontSize: sizes.fontSmall, fontWeight: '600' },
  body: { alignItems: 'center', paddingVertical: 6 },
  icon: { fontSize: 56, marginBottom: 10 },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: colors.navy,
    textAlign: 'center',
    marginBottom: 12,
  },
  line: {
    fontSize: sizes.fontBody,
    color: colors.darkText,
    textAlign: 'center',
    lineHeight: 27,
  },
  mockWrap: { marginTop: 16, width: '100%', alignItems: 'center' },
  dots: { flexDirection: 'row', justifyContent: 'center', gap: 7, marginTop: 18 },
  dot: { width: 9, height: 9, borderRadius: 5, backgroundColor: '#D5DEE8' },
  dotOn: { backgroundColor: colors.primary, width: 22 },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  prevBtn: {
    flex: 1,
    height: sizes.minTouch,
    borderRadius: sizes.radiusSm,
    borderWidth: 1.5,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnHidden: { opacity: 0 },
  prevText: { color: colors.primary, fontSize: sizes.fontBody, fontWeight: '700' },
  nextBtn: {
    flex: 2,
    height: sizes.minTouch,
    borderRadius: sizes.radiusSm,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
});

// ─── 미니 목업 스타일 ───
const m = StyleSheet.create({
  row: { flexDirection: 'row', gap: 10, justifyContent: 'center' },
  favCard: {
    width: 92,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: colors.light,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  favCardAdd: { borderStyle: 'dashed', borderColor: colors.primary, backgroundColor: '#F2F8FE' },
  favIcon: { fontSize: 26 },
  favLabel: { fontSize: 14, fontWeight: '700', color: colors.navy, marginTop: 4 },
  searchBox: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.light,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 10,
  },
  searchText: { flex: 1, fontSize: 15, color: colors.darkText },
  searchBtn: {
    backgroundColor: colors.primary,
    borderRadius: 9,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  searchBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  mode: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: '#fff',
  },
  modeOn: { borderColor: colors.primary, backgroundColor: '#EAF3FC' },
  modeIcon: { fontSize: 22 },
  modeText: { fontSize: 13, color: colors.gray, fontWeight: '600', marginTop: 3 },
  modeTextOn: { color: colors.primary },
  routeCard: {
    width: '100%',
    backgroundColor: colors.light,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 14,
  },
  routeTime: { fontSize: 28, fontWeight: '800', color: colors.navy },
  routeMin: { fontSize: 16, fontWeight: '600' },
  routeDesc: { fontSize: 14, color: '#2DB400', fontWeight: '700', marginTop: 4 },
  guideCard: {
    width: '100%',
    backgroundColor: colors.light,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  guideDist: { fontSize: 16, color: colors.darkText },
  guideNum: { fontSize: 26, fontWeight: '800', color: '#E8590C' },
  guideAlert: {
    marginTop: 8,
    fontSize: 14,
    fontWeight: '700',
    color: '#8A6D00',
    backgroundColor: '#FFF3CD',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
});
