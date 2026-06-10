/** 자주 가는 곳 추가 폼 — 편집 모드 상단에 표시 */
import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { colors, sizes } from '../theme';
import { geocode, type Coord } from '../api/client';
import PlaceSearchInput from './PlaceSearchInput';
import type { FavoritePlace } from '../data/favorites';

const ICONS = ['🏠', '🏢', '🏥', '🏫', '🛒', '👨‍👩‍👧', '⛪', '🏛️', '🏋️', '🍽️', '☕', '📚'];

interface Props {
  onAdd: (place: FavoritePlace) => void;
}

export default function AddFavoriteForm({ onAdd }: Props) {
  const [icon, setIcon] = useState('🏠');
  const [label, setLabel] = useState('');
  const [address, setAddress] = useState('');
  const [picked, setPicked] = useState<Coord | null>(null); // 자동완성 선택 좌표
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async () => {
    if (!label.trim() || !address.trim()) {
      setMsg('이름과 주소를 모두 입력하세요');
      return;
    }
    setBusy(true);
    setMsg(null);
    // 자동완성에서 고른 좌표가 있으면 재조회 없이 사용
    const coord = picked ?? (await geocode(address.trim()));
    setBusy(false);
    if (!coord) {
      setMsg('주소를 찾을 수 없습니다. 다시 입력해주세요');
      return;
    }
    onAdd({
      icon,
      label: label.trim(),
      address: coord.name || address.trim(),
      lng: coord.lng,
      lat: coord.lat,
    });
    setLabel('');
    setAddress('');
    setPicked(null);
    setMsg(null);
  };

  return (
    <View style={styles.form}>
      <Text style={styles.formTitle}>＋ 새 장소 추가</Text>

      <View style={styles.iconRow}>
        {ICONS.map((ic) => (
          <Pressable
            key={ic}
            style={[styles.iconChip, icon === ic && styles.iconChipActive]}
            onPress={() => setIcon(ic)}
          >
            <Text style={styles.iconText}>{ic}</Text>
          </Pressable>
        ))}
      </View>

      <TextInput
        style={styles.input}
        placeholder="장소 이름 (예: 회사)"
        placeholderTextColor={colors.grayLight}
        value={label}
        onChangeText={setLabel}
      />
      <PlaceSearchInput
        placeholder="주소 또는 장소명 (예: 수원역)"
        value={address}
        onChangeText={(t) => {
          setAddress(t);
          setPicked(null); // 직접 수정하면 선택 좌표 무효
        }}
        onSelect={(c) => {
          setPicked(c);
          setMsg(null);
        }}
      />

      {msg && <Text style={styles.msg}>{msg}</Text>}

      <Pressable
        style={({ pressed }) => [styles.addBtn, pressed && { opacity: 0.85 }]}
        onPress={submit}
        disabled={busy}
      >
        <Text style={styles.addBtnText}>{busy ? '확인 중...' : '추가하기'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  form: {
    backgroundColor: colors.card,
    borderRadius: sizes.radius,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 14,
    marginBottom: 14,
  },
  formTitle: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.navy, marginBottom: 12 },
  iconRow: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -3, marginBottom: 10 },
  iconChip: {
    width: 44,
    height: 44,
    margin: 3,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconChipActive: { borderColor: colors.primary, backgroundColor: colors.light },
  iconText: { fontSize: 22 },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: sizes.radiusSm,
    paddingHorizontal: 14,
    height: 48,
    fontSize: sizes.fontSmall,
    color: colors.darkText,
    marginBottom: 10,
  },
  msg: { color: colors.danger, fontSize: sizes.fontSmall, marginBottom: 8 },
  addBtn: {
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addBtnText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
});
