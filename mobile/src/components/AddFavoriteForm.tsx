/** 자주 가는 곳 추가/편집 폼 — 편집 모드 상단에 표시.
 *  initial 이 주어지면 '편집' 모드: 기존 값으로 채워지고 저장 시 onAdd 로 수정본 전달.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { colors, sizes } from '../theme';
import { geocode, type Coord } from '../api/client';
import PlaceSearchInput from './PlaceSearchInput';
import type { FavoritePlace } from '../data/favorites';

const ICONS = [
  '🏠', '🏢', '🏥', '🏫', '🛒', '👨‍👩‍👧', '⛪', '🏛️', '🏋️', '🍽️', '☕', '📚',
  '🚇', '🚌', '🚉', '🚏', '✈️', '🏦', '💊', '🏪', '🌳', '🎬', '💇', '🐾',
];

interface Props {
  onAdd: (place: FavoritePlace) => void;
  /** 편집할 기존 장소 (있으면 편집 모드) */
  initial?: FavoritePlace | null;
  /** 편집 취소 */
  onCancel?: () => void;
}

export default function AddFavoriteForm({ onAdd, initial = null, onCancel }: Props) {
  const [icon, setIcon] = useState('🏠');
  const [label, setLabel] = useState('');
  const [address, setAddress] = useState('');
  const [picked, setPicked] = useState<Coord | null>(null); // 자동완성 선택 좌표
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const isEdit = !!initial;

  // 편집 대상이 바뀌면 폼을 기존 값으로 채움
  useEffect(() => {
    if (initial) {
      setIcon(initial.icon);
      setLabel(initial.label);
      setAddress(initial.address);
      setPicked(null);
      setMsg(null);
    } else {
      setIcon('🏠');
      setLabel('');
      setAddress('');
      setPicked(null);
      setMsg(null);
    }
  }, [initial]);

  const submit = async () => {
    if (!label.trim() || !address.trim()) {
      setMsg('이름과 주소를 모두 입력하세요');
      return;
    }
    setBusy(true);
    setMsg(null);
    // 편집인데 주소를 안 바꿨으면 기존 좌표 재사용 (geocode 생략)
    const coord =
      picked ??
      (isEdit && initial && address.trim() === initial.address
        ? { name: initial.address, address: initial.address, lng: initial.lng, lat: initial.lat }
        : await geocode(address.trim()));
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
      <Text style={styles.formTitle}>{isEdit ? '✏️ 장소 편집' : '＋ 새 장소 추가'}</Text>

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

      <View style={styles.btnRow}>
        {isEdit && onCancel && (
          <Pressable
            style={({ pressed }) => [styles.cancelBtn, pressed && { opacity: 0.85 }]}
            onPress={onCancel}
            accessibilityRole="button"
            accessibilityLabel="편집 취소"
          >
            <Text style={styles.cancelBtnText}>취소</Text>
          </Pressable>
        )}
        <Pressable
          style={({ pressed }) => [styles.addBtn, pressed && { opacity: 0.85 }]}
          onPress={submit}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel={isEdit ? '장소 저장' : '장소 추가'}
        >
          <Text style={styles.addBtnText}>
            {busy ? '확인 중...' : isEdit ? '저장하기' : '추가하기'}
          </Text>
        </Pressable>
      </View>
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
  btnRow: { flexDirection: 'row', gap: 10 },
  cancelBtn: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cancelBtnText: { color: colors.gray, fontSize: sizes.fontBody, fontWeight: '700' },
  addBtn: {
    flex: 2,
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addBtnText: { color: '#fff', fontSize: sizes.fontBody, fontWeight: '700' },
});
