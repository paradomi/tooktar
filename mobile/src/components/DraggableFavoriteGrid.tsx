/** 드래그로 순서 변경 가능한 2열 자주가는곳 그리드 (편집 모드 전용)
 *  reanimated + gesture-handler. 카드를 길게 눌러 끌면 슬롯 순서가 재배치된다.
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet, useWindowDimensions } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  runOnJS,
  withTiming,
  Easing,
} from 'react-native-reanimated';

// 부드러운 정착용 공통 timing 설정 (반동 없음)
const SETTLE = { duration: 220, easing: Easing.out(Easing.cubic) };
import { colors, sizes } from '../theme';
import type { FavoritePlace } from '../data/favorites';

const COLS = 2;
const GAP = 12;
const ROW_H = 132; // 카드 높이(120) + 세로 간격

interface Props {
  items: FavoritePlace[];
  onReorder: (next: FavoritePlace[]) => void;
  onDelete: (index: number) => void;
}

/** index → 그리드 좌표 (행/열) */
function slotPos(index: number, cellW: number) {
  const row = Math.floor(index / COLS);
  const col = index % COLS;
  return { x: col * (cellW + GAP), y: row * ROW_H };
}

/** 드래그 위치 → 가장 가까운 슬롯 index */
function posToIndex(x: number, y: number, cellW: number, count: number) {
  const col = Math.max(0, Math.min(COLS - 1, Math.round(x / (cellW + GAP))));
  const row = Math.max(0, Math.round(y / ROW_H));
  return Math.max(0, Math.min(count - 1, row * COLS + col));
}

export default function DraggableFavoriteGrid({ items, onReorder, onDelete }: Props) {
  const { width } = useWindowDimensions();
  // 좌우 패딩 18*2 가정 → ScrollView 안쪽 폭
  const containerW = width - 36;
  const cellW = (containerW - GAP) / COLS;

  const rows = Math.ceil(items.length / COLS);
  const gridH = rows * ROW_H;

  return (
    <View style={{ height: gridH }}>
      {items.map((item, index) => (
        <DraggableCard
          key={`${item.label}-${item.lat}-${item.lng}`}
          item={item}
          index={index}
          count={items.length}
          cellW={cellW}
          items={items}
          onReorder={onReorder}
          onDelete={() => onDelete(index)}
        />
      ))}
    </View>
  );
}

interface CardProps {
  item: FavoritePlace;
  index: number;
  count: number;
  cellW: number;
  items: FavoritePlace[];
  onReorder: (next: FavoritePlace[]) => void;
  onDelete: () => void;
}

function DraggableCard({ item, index, count, cellW, items, onReorder, onDelete }: CardProps) {
  const base = slotPos(index, cellW);
  const tx = useSharedValue(base.x);
  const ty = useSharedValue(base.y);
  const scale = useSharedValue(1);
  const lifted = useSharedValue(0); // 0=정착, 1=드래그 중
  const [active, setActive] = useState(false);

  // index가 바뀌면(재정렬됨) 새 슬롯으로 부드럽게 이동. 단, 드래그 중인 카드는 제외.
  React.useEffect(() => {
    if (active) return;
    const p = slotPos(index, cellW);
    tx.value = withTiming(p.x, SETTLE);
    ty.value = withTiming(p.y, SETTLE);
  }, [index, cellW, active]);

  const commitReorder = (toIndex: number) => {
    if (toIndex === index) return;
    // 스왑: 드래그한 카드와 놓은 위치의 카드만 자리를 맞바꾼다 (사이 카드는 안 밀림)
    const next = [...items];
    [next[index], next[toIndex]] = [next[toIndex], next[index]];
    onReorder(next);
  };

  const pan = Gesture.Pan()
    .activateAfterLongPress(200)
    .onStart(() => {
      lifted.value = 1;
      scale.value = withTiming(1.05, { duration: 140, easing: Easing.out(Easing.quad) });
      runOnJS(setActive)(true);
    })
    .onUpdate((e) => {
      // 드래그 중에는 애니메이션 없이 손가락을 그대로 추적 (출렁임 방지)
      tx.value = base.x + e.translationX;
      ty.value = base.y + e.translationY;
    })
    .onEnd(() => {
      const toIndex = posToIndex(tx.value, ty.value, cellW, count);
      lifted.value = 0;
      scale.value = withTiming(1, { duration: 160, easing: Easing.out(Easing.quad) });
      // 목표 슬롯으로 부드럽게 정착 (재정렬되면 useEffect가, 아니면 원위치로)
      const p = slotPos(toIndex, cellW);
      tx.value = withTiming(p.x, SETTLE);
      ty.value = withTiming(p.y, SETTLE);
      runOnJS(setActive)(false);
      runOnJS(commitReorder)(toIndex);
    });

  const aStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: tx.value }, { translateY: ty.value }, { scale: scale.value }],
    zIndex: lifted.value ? 10 : 1,
    shadowOpacity: 0.08 + lifted.value * 0.17,
  }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View style={[styles.card, { width: cellW }, aStyle]}>
        <View style={styles.deleteBtn}>
          <Text style={styles.deleteText} onPress={onDelete}>
            ✕
          </Text>
        </View>
        <Text style={styles.dragHint}>⠿</Text>
        <Text style={styles.icon}>{item.icon}</Text>
        <Text style={styles.label} numberOfLines={1}>
          {item.label}
        </Text>
        <Text style={styles.address} numberOfLines={1}>
          {item.address}
        </Text>
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'absolute',
    height: 120,
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#1F3A5E',
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  deleteBtn: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: colors.danger,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
  },
  deleteText: { color: '#fff', fontSize: 16, fontWeight: '700', lineHeight: 20, paddingHorizontal: 6 },
  dragHint: { position: 'absolute', top: 8, left: 10, color: colors.grayLight, fontSize: 16 },
  icon: { fontSize: 34, marginBottom: 8 },
  label: { fontSize: 20, fontWeight: '700', color: colors.navy },
  address: { fontSize: sizes.fontSmall, color: colors.gray, marginTop: 4 },
});
