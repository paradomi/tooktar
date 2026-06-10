/** 설정 화면 — pages/3_설정.py 이식 (글자 크기) */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, sizes } from '../theme';
import { useSettings, FONT_LEVELS } from '../store/SettingsContext';
import type { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Settings'>;

export default function SettingsScreen({ navigation }: Props) {
  const { fontLevel, scale, updateFontLevel } = useSettings();

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>‹ 뒤로</Text>
        </Pressable>
        <Text style={styles.headerTitle}>설정</Text>
      </View>

      <View style={styles.body}>
        <Text style={styles.sectionTitle}>🔤 글자 크기</Text>
        <View style={styles.row}>
          {FONT_LEVELS.map((opt) => {
            const sel = fontLevel === opt;
            return (
              <Pressable
                key={opt}
                style={[styles.sizeBtn, sel && styles.sizeBtnActive]}
                onPress={() => updateFontLevel(opt)}
                accessibilityRole="button"
                accessibilityState={{ selected: sel }}
              >
                <Text style={[styles.sizeText, sel && styles.sizeTextActive]}>{opt}</Text>
              </Pressable>
            );
          })}
        </View>
        <Text style={styles.hint}>선택한 글자 크기는 앱 전체에 적용됩니다.</Text>

        {/* 미리보기 */}
        <View style={styles.preview}>
          <Text style={styles.previewLabel}>미리보기</Text>
          <Text style={[styles.previewText, { fontSize: Math.round(18 * scale) }]}>
            가나다 라마바 — 툭 타로 편하게 이동하세요.
          </Text>
        </View>
      </View>
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
  backText: { fontSize: 18, color: colors.primary, fontWeight: '700' },
  headerTitle: { flex: 1, fontSize: 20, fontWeight: '700', color: colors.navy },
  body: { padding: 18 },
  sectionTitle: { fontSize: 22, fontWeight: '700', color: colors.navy, marginBottom: 16 },
  row: { flexDirection: 'row', marginHorizontal: -4 },
  sizeBtn: {
    flex: 1,
    marginHorizontal: 4,
    minHeight: sizes.minTouch + 4,
    borderRadius: sizes.radiusSm,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.card,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sizeBtnActive: { borderColor: colors.primary, backgroundColor: colors.primary },
  sizeText: { fontSize: 15, fontWeight: '700', color: colors.gray },
  sizeTextActive: { color: '#fff' },
  hint: { marginTop: 16, fontSize: sizes.fontSmall, color: colors.gray },
  preview: {
    marginTop: 24,
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  previewLabel: { fontSize: sizes.fontSmall, color: colors.grayLight, marginBottom: 8 },
  previewText: { color: colors.darkText, fontWeight: '600' },
});
