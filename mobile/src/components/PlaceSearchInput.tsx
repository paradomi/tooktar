/** 장소 자동완성 입력 — 입력 중 카카오 키워드 검색 결과를 드롭다운으로 표시.
 *  선택 시 좌표(Coord)까지 확정해 onSelect로 전달.
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { colors, sizes } from '../theme';
import { searchPlaces, type PlaceResult, type Coord } from '../api/client';

interface Props {
  placeholder: string;
  value: string;
  onChangeText: (text: string) => void;
  onSelect: (coord: Coord) => void;
  onSubmit?: () => void;
}

export default function PlaceSearchInput({
  placeholder,
  value,
  onChangeText,
  onSelect,
  onSubmit,
}: Props) {
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 선택 직후엔 그 변경으로 다시 검색하지 않도록 가드
  const skipNext = useRef(false);

  useEffect(() => {
    if (skipNext.current) {
      skipNext.current = false;
      return;
    }
    if (timer.current) clearTimeout(timer.current);
    const q = value.trim();
    // GPS 표시(📍)거나 너무 짧으면 검색 안 함
    if (q.length < 2 || q.startsWith('📍')) {
      setResults([]);
      setOpen(false);
      return;
    }
    timer.current = setTimeout(async () => {
      setLoading(true);
      const r = await searchPlaces(q);
      setLoading(false);
      setResults(r);
      setOpen(r.length > 0);
    }, 300); // 디바운스 300ms
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [value]);

  const pick = (p: PlaceResult) => {
    skipNext.current = true;
    onChangeText(p.place_name);
    onSelect({
      name: p.place_name,
      address: p.address,
      lng: p.lng as number,
      lat: p.lat as number,
    });
    setOpen(false);
    setResults([]);
  };

  // 엔터(검색): 결과가 있으면 첫 항목 자동 선택, 드롭다운 닫기
  const handleSubmit = () => {
    if (results.length > 0) {
      pick(results[0]);
    } else {
      setOpen(false);
    }
    onSubmit?.();
  };

  // 포커스 빠지면 드롭다운 닫기 (항목 탭이 먼저 처리되도록 약간 지연)
  const handleBlur = () => {
    setTimeout(() => setOpen(false), 150);
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder={placeholder}
          placeholderTextColor={colors.grayLight}
          value={value}
          onChangeText={onChangeText}
          returnKeyType="search"
          onSubmitEditing={handleSubmit}
          onBlur={handleBlur}
          autoCorrect={false}
        />
        {loading && <ActivityIndicator style={styles.spinner} color={colors.primary} />}
      </View>

      {open && (
        <View style={styles.dropdown}>
          {results.map((p, i) => (
            <Pressable
              key={`${p.place_name}-${i}`}
              style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
              onPress={() => pick(p)}
            >
              <Text style={styles.itemName} numberOfLines={1}>
                {p.place_name}
              </Text>
              {!!p.address && (
                <Text style={styles.itemAddr} numberOfLines={1}>
                  {p.address}
                </Text>
              )}
            </Pressable>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 12, zIndex: 5 },
  inputRow: { justifyContent: 'center' },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: sizes.radiusSm,
    paddingHorizontal: 16,
    paddingRight: 44,
    height: 54,
    fontSize: sizes.fontBody,
    color: colors.darkText,
  },
  spinner: { position: 'absolute', right: 14 },
  dropdown: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: sizes.radiusSm,
    marginTop: 4,
    overflow: 'hidden',
  },
  item: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemPressed: { backgroundColor: colors.light },
  itemName: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.navy },
  itemAddr: { fontSize: 13, color: colors.gray, marginTop: 2 },
});
