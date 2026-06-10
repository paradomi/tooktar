/** 모드 선택 카드 (빠른길/휠체어/덜걷기) */
import React from 'react';
import { Pressable, Text, StyleSheet, View } from 'react-native';
import { colors, sizes } from '../theme';
import type { RouteMode } from '../data/modes';

interface Props {
  mode: RouteMode;
  selected: boolean;
  onPress: (key: RouteMode['key']) => void;
}

export default function ModeCard({ mode, selected, onPress }: Props) {
  return (
    <Pressable
      style={[styles.card, selected && styles.cardActive]}
      onPress={() => onPress(mode.key)}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      accessibilityLabel={`${mode.name}, ${mode.sub}`}
    >
      <Text style={styles.icon}>{mode.icon}</Text>
      <View style={styles.textWrap}>
        <Text style={[styles.name, selected && styles.nameActive]}>{mode.name}</Text>
        <Text style={[styles.sub, selected && styles.subActive]}>{mode.sub}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: sizes.minTouch + 28,
    backgroundColor: colors.card,
    borderRadius: sizes.radiusSm,
    borderWidth: 2,
    borderColor: colors.border,
    paddingVertical: 12,
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardActive: {
    borderColor: colors.primary,
    backgroundColor: colors.light,
  },
  icon: { fontSize: 26, marginBottom: 4 },
  textWrap: { alignItems: 'center' },
  name: { fontSize: 16, fontWeight: '700', color: colors.gray },
  nameActive: { color: colors.navy },
  sub: { fontSize: 12, color: colors.grayLight, marginTop: 2 },
  subActive: { color: colors.primary },
});
