/** 자주 가는 곳 카드 — 큰 터치 영역, 한 번 누르면 도착지 설정 */
import React from 'react';
import { Pressable, Text, StyleSheet } from 'react-native';
import { colors, sizes } from '../theme';
import type { FavoritePlace } from '../data/favorites';

interface Props {
  place: FavoritePlace;
  onPress: (place: FavoritePlace) => void;
  editing?: boolean;
  onDelete?: () => void;
}

export default function FavoriteCard({ place, onPress, editing, onDelete }: Props) {
  return (
    <Pressable
      style={({ pressed }) => [styles.card, pressed && !editing && styles.pressed]}
      onPress={() => !editing && onPress(place)}
      disabled={editing}
      accessibilityRole="button"
      accessibilityLabel={`${place.label}, ${place.address}로 경로 찾기`}
    >
      {editing && (
        <Pressable
          style={styles.deleteBtn}
          onPress={onDelete}
          accessibilityRole="button"
          accessibilityLabel={`${place.label} 삭제`}
          hitSlop={8}
        >
          <Text style={styles.deleteText}>✕</Text>
        </Pressable>
      )}
      <Text style={styles.icon}>{place.icon}</Text>
      <Text style={styles.label} numberOfLines={1}>
        {place.label}
      </Text>
      <Text style={styles.address} numberOfLines={1}>
        {place.address}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: 120,
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 18,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#1F3A5E',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  pressed: { backgroundColor: colors.light, transform: [{ scale: 0.98 }] },
  icon: { fontSize: 34, marginBottom: 8 },
  label: { fontSize: 20, fontWeight: '700', color: colors.navy },
  address: { fontSize: sizes.fontSmall, color: colors.gray, marginTop: 4 },
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
  deleteText: { color: '#fff', fontSize: 16, fontWeight: '700', lineHeight: 18 },
});
