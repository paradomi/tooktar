/** 홈 화면 — Streamlit app.py 의 홈/검색 UI 이식
 *  로고 · 자주 가는 곳 · 출발/도착 입력 · 경로 찾기
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors, sizes } from '../theme';
import { DEFAULT_ORIGIN, type FavoritePlace } from '../data/favorites';
import FavoriteCard from '../components/FavoriteCard';
import AddFavoriteForm from '../components/AddFavoriteForm';
import DraggableFavoriteGrid from '../components/DraggableFavoriteGrid';
import PlaceSearchInput from '../components/PlaceSearchInput';
import { useFavorites } from '../store/favorites';
import { useRecents } from '../store/recents';
import { checkHealth, geocode, coordToAddress, type Coord } from '../api/client';
import { getCurrentCoord } from '../utils/location';
import type { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export default function HomeScreen({ navigation }: Props) {
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  // GPS로 잡은 현재 위치 좌표 (출발지 기본값)
  const [gpsCoord, setGpsCoord] = useState<Coord | null>(null);
  // 자동완성에서 선택한 좌표 (있으면 geocode 재호출 없이 바로 사용)
  const [originPicked, setOriginPicked] = useState<Coord | null>(null);
  const [destPicked, setDestPicked] = useState<Coord | null>(null);
  // 자주 가는 곳 (영구 저장) + 편집 모드
  const { favorites, addFavorite, removeFavorite, reorderFavorites } = useFavorites();
  const { recents, addRecent, removeRecent, clearRecents } = useRecents();
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    checkHealth().then(setBackendUp);
    // 현재 위치 자동 감지 → 출발지 기본값
    (async () => {
      const c = await getCurrentCoord();
      if (!c) return;
      const addr = await coordToAddress(c.lng, c.lat);
      const coord: Coord = addr ?? {
        name: '현재 위치',
        address: '',
        lng: c.lng,
        lat: c.lat,
      };
      setGpsCoord(coord);
      setOrigin(`📍 ${coord.name}`);
    })();
  }, []);

  // 즐겨찾기 → 도착지로 설정 후 경로 탐색
  const onFavorite = (place: FavoritePlace) => {
    const coord: Coord = { name: place.label, address: place.address, lng: place.lng, lat: place.lat };
    setDest(place.address);
    setDestPicked(coord);
    runSearch(place.address, coord);
  };

  const runSearch = async (destText: string, destCoord?: Coord) => {
    if (!destText.trim()) {
      Alert.alert('알림', '도착지를 입력해주세요');
      return;
    }
    setLoading(true);
    try {
      // 출발지 우선순위: 자동완성 선택 → GPS 표시(📍) → 직접입력 geocode → GPS/기본값
      let originCoord: Coord;
      const trimmed = origin.trim();
      if (originPicked) {
        originCoord = originPicked;
      } else if (trimmed.startsWith('📍') && gpsCoord) {
        originCoord = gpsCoord;
      } else if (trimmed) {
        originCoord = (await geocode(trimmed)) ?? gpsCoord ?? { ...DEFAULT_ORIGIN };
      } else {
        originCoord = gpsCoord ?? { ...DEFAULT_ORIGIN };
      }
      // 도착지 우선순위: 인자(즐겨찾기) → 자동완성 선택 → geocode
      const dc: Coord =
        destCoord ?? destPicked ?? (await geocode(destText)) ?? {
          name: destText,
          address: destText,
          lng: 0,
          lat: 0,
        };

      if (!dc.lat || !dc.lng) {
        Alert.alert('알림', '도착지 좌표를 찾을 수 없습니다. 다른 검색어를 시도해주세요.');
        return;
      }
      // 경로 탐색 화면으로 이동 (좌표 전달)
      addRecent(dc); // 최근 검색 기록
      navigation.navigate('Routes', { origin: originCoord, dest: dc });
      // 뒤로 왔을 때 이전 도착지·드롭다운이 남지 않도록 입력 초기화
      setDest('');
      setDestPicked(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* 상단 설정 버튼 */}
        <View style={styles.topBar}>
          <Pressable
            style={styles.settingsBtn}
            onPress={() => navigation.navigate('Settings')}
            accessibilityRole="button"
            accessibilityLabel="설정"
          >
            <Text style={styles.settingsText}>⚙️ 설정</Text>
          </Pressable>
        </View>

        {/* 로고 (글자 크기 설정 영향 없이 고정) */}
        <View style={styles.logoWrap}>
          <Text style={styles.logo} allowFontScaling={false}>
            툭 타
          </Text>
          <Text style={styles.tagline} allowFontScaling={false}>
            " 이동의 장벽을 툭, 넘다. "
          </Text>
        </View>

        {/* 백엔드 상태 */}
        {backendUp === false && (
          <View style={styles.warn}>
            <Text style={styles.warnText}>
              백엔드에 연결할 수 없습니다. uvicorn(:8000)을 실행했는지 확인하세요.
            </Text>
          </View>
        )}

        {/* 자주 가는 곳 */}
        <View style={styles.favHeader}>
          <Text style={styles.sectionTitle}>⭐ 자주 가는 곳</Text>
          <Pressable
            style={styles.editBtn}
            onPress={() => setEditing((v) => !v)}
            accessibilityRole="button"
            accessibilityLabel={editing ? '편집 완료' : '자주 가는 곳 편집'}
          >
            <Text style={styles.editText}>{editing ? '완료' : '✏️ 편집'}</Text>
          </Pressable>
        </View>

        {editing && <AddFavoriteForm onAdd={addFavorite} />}

        {editing ? (
          <>
            <Text style={styles.dragGuide}>카드를 길게 눌러 끌면 순서를 바꿀 수 있어요</Text>
            <DraggableFavoriteGrid
              items={favorites}
              onReorder={reorderFavorites}
              onDelete={removeFavorite}
            />
          </>
        ) : (
          <View style={styles.grid}>
            {favorites.map((p, i) => (
              <View key={`${p.label}-${i}`} style={styles.gridItem}>
                <FavoriteCard place={p} onPress={onFavorite} />
              </View>
            ))}
          </View>
        )}

        {/* 출발/도착 입력 (자동완성) */}
        <Text style={styles.sectionTitle}>🔍 경로 검색</Text>
        <PlaceSearchInput
          placeholder="📍 출발지 (비워두면 현재 위치)"
          value={origin}
          onChangeText={(t) => {
            setOrigin(t);
            setOriginPicked(null); // 직접 수정하면 선택 좌표 무효
          }}
          onSelect={(c) => setOriginPicked(c)}
        />
        <PlaceSearchInput
          placeholder="🏁 도착지를 입력하세요"
          value={dest}
          onChangeText={(t) => {
            setDest(t);
            setDestPicked(null);
          }}
          onSelect={(c) => setDestPicked(c)}
          onSubmit={() => runSearch(dest)}
        />

        <Pressable
          style={({ pressed }) => [styles.searchBtn, pressed && { opacity: 0.85 }]}
          onPress={() => runSearch(dest)}
          disabled={loading}
          accessibilityRole="button"
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.searchBtnText}>경로 찾기</Text>
          )}
        </Pressable>

        {/* 최근 검색 */}
        {recents.length > 0 && (
          <>
            <View style={styles.recentHeader}>
              <Text style={styles.sectionTitle}>🕘 최근 검색</Text>
              <Pressable
                onPress={clearRecents}
                hitSlop={8}
                accessibilityRole="button"
                accessibilityLabel="최근 검색 전체 삭제"
              >
                <Text style={styles.clearAllText}>전체 삭제</Text>
              </Pressable>
            </View>
            {recents.map((rc, i) => (
              <View key={`${rc.name}-${i}`} style={styles.recentRow}>
                <Pressable
                  style={({ pressed }) => [styles.recentMain, pressed && styles.recentPressed]}
                  onPress={() => {
                    setDest(rc.name);
                    setDestPicked(rc);
                    runSearch(rc.name, rc);
                  }}
                  accessibilityRole="button"
                  accessibilityLabel={`${rc.name}로 경로 찾기`}
                >
                  <Text style={styles.recentName} numberOfLines={1}>
                    📍 {rc.name}
                  </Text>
                  {!!rc.address && (
                    <Text style={styles.recentAddr} numberOfLines={1}>
                      {rc.address}
                    </Text>
                  )}
                </Pressable>
                <Pressable
                  style={({ pressed }) => [styles.recentDelete, pressed && { opacity: 0.6 }]}
                  onPress={() => removeRecent(rc)}
                  hitSlop={8}
                  accessibilityRole="button"
                  accessibilityLabel={`${rc.name} 삭제`}
                >
                  <Text style={styles.recentDeleteText}>✕</Text>
                </Pressable>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: 18, paddingBottom: 40 },
  recentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  clearAllText: { fontSize: sizes.fontSmall, color: colors.gray, fontWeight: '700' },
  recentRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: sizes.radiusSm,
    marginBottom: 8,
    overflow: 'hidden',
  },
  recentMain: { flex: 1, paddingHorizontal: 16, paddingVertical: 12 },
  recentPressed: { backgroundColor: colors.light },
  recentName: { fontSize: sizes.fontBody, fontWeight: '700', color: colors.navy },
  recentAddr: { fontSize: sizes.fontSmall, color: colors.gray, marginTop: 2 },
  recentDelete: {
    width: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
  },
  recentDeleteText: { fontSize: sizes.fontBody, color: colors.gray, fontWeight: '700' },
  topBar: { flexDirection: 'row', justifyContent: 'flex-start' },
  settingsBtn: {
    minHeight: 40,
    paddingHorizontal: 14,
    borderRadius: sizes.radiusSm,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingsText: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.navy },
  favHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  editBtn: {
    minHeight: 40,
    paddingHorizontal: 14,
    borderRadius: sizes.radiusSm,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  editText: { fontSize: sizes.fontSmall, fontWeight: '700', color: colors.primary },
  dragGuide: { fontSize: sizes.fontSmall, color: colors.gray, marginBottom: 12 },
  logoWrap: { alignItems: 'center', marginVertical: 20 },
  logo: { fontSize: sizes.fontLogo, fontWeight: '700', color: colors.navy, letterSpacing: 6 },
  tagline: { fontSize: 16, color: colors.gray, marginTop: 12 },
  warn: {
    backgroundColor: '#FDECEA',
    borderRadius: sizes.radiusSm,
    padding: 12,
    marginBottom: 12,
  },
  warnText: { color: colors.danger, fontSize: sizes.fontSmall },
  sectionTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.navy,
    marginTop: 16,
    marginBottom: 12,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 },
  gridItem: { width: '50%', paddingHorizontal: 6, marginBottom: 12 },
  searchBtn: {
    backgroundColor: colors.primary,
    borderRadius: sizes.radiusSm,
    height: sizes.minTouch + 6,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
  },
  searchBtnText: { color: '#fff', fontSize: 20, fontWeight: '700' },
});
