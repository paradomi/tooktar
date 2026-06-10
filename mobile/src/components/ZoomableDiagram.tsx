/** 역내 도면 — 탭하면 전체화면 모달에서 핀치(웹은 핀치/휠) 확대·이동 */
import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  Image,
  Modal,
  Pressable,
  StyleSheet,
  Platform,
  useWindowDimensions,
} from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors } from '../theme';

interface Props {
  uri: string;
  /** 인라인(닫힌 상태) 높이 */
  height?: number;
}

const SETTLE = { duration: 200, easing: Easing.out(Easing.cubic) };
const MAX_SCALE = 5;
const MIN_SCALE = 1;

/** 네이티브 전용 — 핀치 + 팬 + 더블탭 리셋 */
function NativeZoom({ uri }: { uri: string }) {
  const { width, height } = useWindowDimensions();
  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const savedTx = useSharedValue(0);
  const savedTy = useSharedValue(0);

  const pinch = Gesture.Pinch()
    .onUpdate((e) => {
      const next = savedScale.value * e.scale;
      scale.value = Math.min(Math.max(next, MIN_SCALE), MAX_SCALE);
    })
    .onEnd(() => {
      savedScale.value = scale.value;
      if (scale.value <= MIN_SCALE) {
        tx.value = withTiming(0, SETTLE);
        ty.value = withTiming(0, SETTLE);
        savedTx.value = 0;
        savedTy.value = 0;
      }
    });

  const pan = Gesture.Pan()
    .onUpdate((e) => {
      tx.value = savedTx.value + e.translationX;
      ty.value = savedTy.value + e.translationY;
    })
    .onEnd(() => {
      savedTx.value = tx.value;
      savedTy.value = ty.value;
    });

  const doubleTap = Gesture.Tap()
    .numberOfTaps(2)
    .onEnd(() => {
      const zoomIn = scale.value < 2;
      scale.value = withTiming(zoomIn ? 2.5 : 1, SETTLE);
      savedScale.value = zoomIn ? 2.5 : 1;
      if (!zoomIn) {
        tx.value = withTiming(0, SETTLE);
        ty.value = withTiming(0, SETTLE);
        savedTx.value = 0;
        savedTy.value = 0;
      }
    });

  const composed = Gesture.Simultaneous(pinch, pan, doubleTap);

  const animStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: tx.value },
      { translateY: ty.value },
      { scale: scale.value },
    ],
  }));

  return (
    <GestureDetector gesture={composed}>
      <Animated.View style={styles.zoomArea}>
        <Animated.Image
          source={{ uri }}
          style={[{ width, height: height * 0.8 }, animStyle]}
          resizeMode="contain"
          accessibilityLabel="역내 도면 (확대)"
        />
      </Animated.View>
    </GestureDetector>
  );
}

/** 웹 전용 — 휠/핀치 줌 + 드래그 이동 (DOM) */
function WebZoom({ uri }: { uri: string }) {
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  const clamp = (s: number) => Math.min(Math.max(s, MIN_SCALE), MAX_SCALE);

  return React.createElement(
    'div',
    {
      style: {
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        touchAction: 'none',
        cursor: scale > 1 ? 'grab' : 'default',
      },
      onWheel: (e: any) => {
        e.preventDefault();
        const delta = -e.deltaY * 0.0015;
        setScale((s) => {
          const ns = clamp(s + delta * s);
          if (ns <= MIN_SCALE) setPos({ x: 0, y: 0 });
          return ns;
        });
      },
      onPointerDown: (e: any) => {
        if (scale <= 1) return;
        drag.current = { x: e.clientX, y: e.clientY, ox: pos.x, oy: pos.y };
        e.currentTarget.setPointerCapture?.(e.pointerId);
      },
      onPointerMove: (e: any) => {
        if (!drag.current) return;
        setPos({
          x: drag.current.ox + (e.clientX - drag.current.x),
          y: drag.current.oy + (e.clientY - drag.current.y),
        });
      },
      onPointerUp: () => {
        drag.current = null;
      },
      onDoubleClick: () => {
        setScale((s) => (s < 2 ? 2.5 : 1));
        setPos({ x: 0, y: 0 });
      },
    },
    React.createElement('img', {
      src: uri,
      alt: '역내 도면 (확대)',
      draggable: false,
      style: {
        maxWidth: '100%',
        maxHeight: '100%',
        objectFit: 'contain',
        transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`,
        transition: drag.current ? 'none' : 'transform 0.08s ease-out',
      },
    })
  );
}

export default function ZoomableDiagram({ uri, height = 360 }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* 인라인 미리보기 — 탭하면 확대 모달 */}
      <Pressable
        onPress={() => setOpen(true)}
        accessibilityRole="imagebutton"
        accessibilityLabel="역내 도면, 탭하면 확대"
        style={styles.inlineWrap}
      >
        {Platform.OS === 'web'
          ? React.createElement('img', {
              src: uri,
              alt: '역내 도면',
              style: { width: '100%', height, objectFit: 'contain', display: 'block' },
            })
          : (
            <Image
              source={{ uri }}
              style={{ width: '100%', height }}
              resizeMode="contain"
              accessibilityLabel="역내 도면"
            />
          )}
        <View style={styles.zoomHint} pointerEvents="none">
          <Text style={styles.zoomHintText}>⤢ 탭하여 확대</Text>
        </View>
      </Pressable>

      <Modal
        visible={open}
        transparent={false}
        animationType="fade"
        onRequestClose={() => setOpen(false)}
      >
        <View style={styles.modalRoot}>
          {Platform.OS === 'web' ? <WebZoom uri={uri} /> : <NativeZoom uri={uri} />}

          <Pressable
            style={styles.closeBtn}
            onPress={() => setOpen(false)}
            accessibilityRole="button"
            accessibilityLabel="닫기"
            hitSlop={10}
          >
            <Text style={styles.closeBtnText}>✕ 닫기</Text>
          </Pressable>

          <View style={styles.hintBar} pointerEvents="none">
            <Text style={styles.hintBarText}>
              {Platform.OS === 'web'
                ? '휠/핀치로 확대 · 드래그로 이동 · 더블클릭 리셋'
                : '두 손가락으로 확대 · 드래그로 이동 · 더블탭 리셋'}
            </Text>
          </View>
        </View>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  inlineWrap: { width: '100%', position: 'relative' },
  zoomHint: {
    position: 'absolute',
    right: 8,
    bottom: 8,
    backgroundColor: 'rgba(0,0,0,0.55)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  zoomHintText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  modalRoot: { flex: 1, backgroundColor: '#000' },
  zoomArea: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  closeBtn: {
    position: 'absolute',
    top: 40,
    right: 16,
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  closeBtnText: { fontSize: 16, fontWeight: '700', color: colors.navy },
  hintBar: {
    position: 'absolute',
    bottom: 28,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  hintBarText: {
    color: '#fff',
    fontSize: 13,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
  },
});
