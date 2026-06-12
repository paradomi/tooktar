/** 코치마크 오버레이 — 실제 화면 요소에 스포트라이트(구멍 뚫린 어두운 막) + 맥동 링 + 말풍선.
 *  화면 전체가 터치를 통과해 스크롤과 조작이 자유롭다.
 *  rect 가 null 이면 중앙 안내 카드(인트로/마무리)로 표시.
 */
import React, { useEffect, useRef } from 'react';
import { View, Text, Pressable, Animated, Easing, StyleSheet, ScrollView, useWindowDimensions } from 'react-native';
import { colors, sizes } from '../theme';

export interface SpotRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Props {
  visible: boolean;
  rect: SpotRect | null;
  title?: string;
  text: string;
  step: number;
  total: number;
  onSkip: () => void;
  onClose: () => void;
  /** 있으면 말풍선에 진행 버튼 표시 (인트로 '시작하기' / 마지막 '완료') */
  actionLabel?: string;
  onAction?: () => void;
}

const DIM = 'rgba(0,18,40,0.62)';
const PAD = 6; // 구멍 여유

export default function CoachMark({
  visible,
  rect,
  title,
  text,
  step,
  total,
  onSkip,
  onClose,
  actionLabel,
  onAction,
}: Props) {
  const { width: winW, height: winH } = useWindowDimensions();
  const pulse = useRef(new Animated.Value(0)).current;
  const bubbleIn = useRef(new Animated.Value(0)).current;

  // 스포트라이트 링 맥동
  useEffect(() => {
    if (!visible) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 900, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 900, easing: Easing.inOut(Easing.quad), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [visible, pulse]);

  // 단계 바뀔 때 말풍선 등장 애니메이션
  useEffect(() => {
    if (!visible) return;
    bubbleIn.setValue(0);
    Animated.timing(bubbleIn, {
      toValue: 1,
      duration: 260,
      easing: Easing.out(Easing.back(1.2)),
      useNativeDriver: true,
    }).start();
  }, [visible, step, rect, bubbleIn]);

  if (!visible) return null;

  const hole = rect
    ? {
        x: Math.max(0, rect.x - PAD),
        y: Math.max(0, rect.y - PAD),
        w: rect.w + PAD * 2,
        h: rect.h + PAD * 2,
      }
    : null;

  // 말풍선 위치: 구멍 아래 공간이 충분하면 아래, 아니면 위
  const bubbleW = Math.min(330, winW - 28);
  let bubbleLeft = (winW - bubbleW) / 2;
  let arrowUp = false; // 말풍선이 구멍 '아래'에 있으면 위쪽 화살표
  // 구멍을 절대 가리지 않도록, 위/아래 중 넓은 쪽 공간 안에서만 말풍선을 배치한다.
  // 아래쪽이면 top 고정(구멍 바로 아래), 위쪽이면 bottom 고정(구멍 바로 위)으로 앵커.
  let bubbleTop: number | undefined = winH / 2 - 120; // 인트로(구멍 없음) 기본
  let bubbleBottom: number | undefined;
  let bubbleMaxH = winH - bubbleTop - 14;
  if (hole) {
    const spaceBelow = winH - (hole.y + hole.h + 14) - 14;
    const spaceAbove = hole.y - 14 - 14;
    if (spaceBelow >= spaceAbove) {
      bubbleTop = hole.y + hole.h + 14;
      bubbleBottom = undefined;
      bubbleMaxH = spaceBelow;
      arrowUp = true;
    } else {
      bubbleTop = undefined;
      bubbleBottom = winH - (hole.y - 14); // 구멍 바로 위에 하단 앵커
      bubbleMaxH = spaceAbove;
    }
    bubbleLeft = Math.min(Math.max(14, hole.x + hole.w / 2 - bubbleW / 2), winW - bubbleW - 14);
  }
  const arrowX = hole ? Math.min(Math.max(18, hole.x + hole.w / 2 - bubbleLeft - 9), bubbleW - 36) : 0;

  const ringScale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.06] });
  const ringOpacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.95, 0.45] });

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {hole ? (
        <>
          {/* 구멍 주변 4면 어두운 막 (터치 통과 — 스크롤/탭 그대로 가능) — 구멍 안쪽은 실제 버튼이 눌림 */}
          <View pointerEvents="none" style={[styles.dim, { left: 0, top: 0, right: 0, height: hole.y }]} />
          <View pointerEvents="none" style={[styles.dim, { left: 0, top: hole.y, width: hole.x, height: hole.h }]} />
          <View
            pointerEvents="none"
            style={[styles.dim, { left: hole.x + hole.w, top: hole.y, right: 0, height: hole.h }]}
          />
          <View pointerEvents="none" style={[styles.dim, { left: 0, top: hole.y + hole.h, right: 0, bottom: 0 }]} />
          {/* 맥동 링 */}
          <Animated.View
            pointerEvents="none"
            style={[
              styles.ring,
              {
                left: hole.x - 3,
                top: hole.y - 3,
                width: hole.w + 6,
                height: hole.h + 6,
                opacity: ringOpacity,
                transform: [{ scale: ringScale }],
              },
            ]}
          />
        </>
      ) : (
        <View pointerEvents="none" style={[styles.dim, StyleSheet.absoluteFill]} />
      )}

      {/* 말풍선 */}
      <Animated.View
        pointerEvents="auto"
        style={[
          styles.bubble,
          {
            ...(bubbleTop != null ? { top: bubbleTop } : { bottom: bubbleBottom }),
            left: bubbleLeft,
            width: bubbleW,
            maxHeight: bubbleMaxH,
            opacity: bubbleIn,
            transform: [
              {
                translateY: bubbleIn.interpolate({
                  inputRange: [0, 1],
                  outputRange: [arrowUp ? 10 : -10, 0],
                }),
              },
            ],
          },
        ]}
      >
        {hole && arrowUp && <View style={[styles.arrow, styles.arrowUp, { left: arrowX }]} />}
        <View style={styles.bubbleHead}>
          <Text style={styles.stepBadge}>
            {step + 1} / {total}
          </Text>
          <View style={styles.headBtns}>
            <Pressable onPress={onSkip} hitSlop={10} accessibilityRole="button" accessibilityLabel="이 단계 건너뛰기">
              <Text style={styles.skip}>건너뛰기 ▸</Text>
            </Pressable>
            <Pressable onPress={onClose} hitSlop={10} accessibilityRole="button" accessibilityLabel="안내 끝내기">
              <Text style={styles.close}>✕</Text>
            </Pressable>
          </View>
        </View>
        <ScrollView style={styles.bodyScroll} bounces={false} showsVerticalScrollIndicator>
          {!!title && <Text style={styles.title}>{title}</Text>}
          <Text style={styles.text}>{text}</Text>
        </ScrollView>
        {actionLabel && onAction && (
          <Pressable
            style={styles.actionBtn}
            onPress={onAction}
            accessibilityRole="button"
            accessibilityLabel={actionLabel}
          >
            <Text style={styles.actionText}>{actionLabel}</Text>
          </Pressable>
        )}
        {!actionLabel && (
          <Text style={styles.hint}>👆 밝게 표시된 곳을 직접 눌러보세요</Text>
        )}
        {hole && !arrowUp && <View style={[styles.arrow, styles.arrowDown, { left: arrowX }]} />}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  dim: { position: 'absolute', backgroundColor: DIM },
  ring: {
    position: 'absolute',
    borderWidth: 3,
    borderColor: '#FFD23F',
    borderRadius: 14,
  },
  bubble: {
    position: 'absolute',
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  bubbleHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  stepBadge: {
    backgroundColor: colors.light,
    color: colors.primary,
    fontWeight: '800',
    fontSize: 13,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    overflow: 'hidden',
  },
  bodyScroll: { flexGrow: 0, flexShrink: 1 },
  headBtns: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  skip: { color: colors.grayLight, fontSize: 13, fontWeight: '600' },
  close: { color: colors.grayLight, fontSize: 15, fontWeight: '600' },
  title: { fontSize: 18, fontWeight: '800', color: colors.navy, marginBottom: 6 },
  text: { fontSize: sizes.fontSmall, color: colors.darkText, lineHeight: 24 },
  hint: { marginTop: 10, fontSize: 13, color: colors.primary, fontWeight: '700' },
  actionBtn: {
    marginTop: 12,
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
  arrow: {
    position: 'absolute',
    width: 0,
    height: 0,
    borderLeftWidth: 9,
    borderRightWidth: 9,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
  },
  arrowUp: { top: -9, borderBottomWidth: 9, borderBottomColor: '#fff' },
  arrowDown: { bottom: -9, borderTopWidth: 9, borderTopColor: '#fff' },
});
