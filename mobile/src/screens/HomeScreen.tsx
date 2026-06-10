/** 홈 화면 — Streamlit app.py 의 홈/검색 UI 이식
 *  로고 · 자주 가는 곳 · 출발/도착 입력 · 경로 찾기
 *  ❓ 사용법: 실제 버튼을 스포트라이트로 짚어주며 직접 눌러 진행하는 인터랙티브 투어
 */
import React, { useEffect, useRef, useState } from 'react';
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
import CoachMark, { type SpotRect } from '../components/CoachMark';
import { checkHealth, waitForBackend, geocode, coordToAddress, type Coord } from '../api/client';
import { getCurrentCoord } from '../utils/location';
import type { RootStackParamList } from '../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

/** 인터랙티브 투어 단계 — target 요소를 스포트라이트, 사용자가 실제 행동을 해야 다음으로 진행 */
type TourTarget = 'edit' | 'form' | 'grid' | 'search' | null;
const TOUR: {
  target: TourTarget;
  title?: string;
  text: string;
  action?: string;
  extraH?: number; // 구멍 아래 여유 (자동완성 드롭다운 등)
}[] = [
  {
    target: null,
    title: '직접 해보며 배우기',
    text: '화면에 밝게 표시되는 버튼을 하나씩 직접 눌러보면서 배우는 안내예요. 언제든 「건너뛰기」로 끝낼 수 있어요.',
    action: '시작하기',
  },
  {
    target: 'edit',
    text: '먼저 ✏️ 편집 버튼을 눌러 보세요. 자주 가는 곳을 추가하고 고칠 수 있는 편집 모드가 열려요.',
  },
  {
    target: 'form',
    text: '연습으로 장소를 하나 만들어 볼게요. 아이콘을 고르고, 이름(예: 연습)과 주소(예: 수원역)를 입력한 뒤 「추가하기」를 누르세요.',
    extraH: 150,
  },
  {
    target: 'grid',
    text: '잘하셨어요! 방금 만든 카드의 오른쪽 위 ✏️ 버튼을 눌러 보세요. 내용을 고칠 수 있어요.',
  },
  {
    target: 'form',
    text: '이름이나 아이콘을 바꿔 보고 「저장하기」를 누르세요. 주소를 그대로 두면 위치는 유지돼요.',
    extraH: 150,
  },
  {
    target: 'grid',
    text: '이번엔 연습용 카드의 ✕ 버튼을 눌러 삭제해 볼까요? 필요 없어진 장소는 언제든 지울 수 있어요.',
  },
  {
    target: 'edit',
    text: '좋아요! 「완료」 버튼을 눌러 편집 모드를 닫아 주세요.',
  },
  {
    target: 'search',
    title: '마지막 단계예요',
    text: '도착지를 입력하고 「경로 찾기」를 누르면 나에게 맞는 경로가 나와요. 이제 직접 한번 검색해 보세요! 🎉',
    action: '완료',
  },
];

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
  const { favorites, addFavorite, removeFavorite, updateFavorite, reorderFavorites } =
    useFavorites();
  const { recents, addRecent, removeRecent, clearRecents } = useRecents();
  const [editing, setEditing] = useState(false);
  // 편집 중인 즐겨찾기 index (null 이면 새 장소 추가 모드)
  const [editIndex, setEditIndex] = useState<number | null>(null);
  // 인터랙티브 투어: 현재 단계 (null=꺼짐)
  const [tour, setTour] = useState<number | null>(null);
  const [tourRect, setTourRect] = useState<SpotRect | null>(null);
  const rootRef = useRef<View>(null);
  const scrollRef = useRef<ScrollView>(null);
  const scrollYRef = useRef(0);
  const editToggleRef = useRef<View>(null);
  const formRef = useRef<View>(null);
  const gridRef = useRef<View>(null);
  const searchRef = useRef<View>(null);

  // 투어 타깃 측정: 단계/레이아웃 변화 시 스포트라이트 위치 갱신 (화면 밖이면 스크롤로 끌어옴)
  useEffect(() => {
    if (tour == null) return;
    const t = TOUR[tour].target;
    if (!t) {
      setTourRect(null);
      return;
    }
    const refMap = { edit: editToggleRef, form: formRef, grid: gridRef, search: searchRef };
    const timer = setTimeout(() => {
      const target = refMap[t].current;
      const host = rootRef.current;
      if (!target || !host) return;
      const apply = () =>
        target.measureInWindow((tx, ty, tw, th) => {
          host.measureInWindow((hx, hy, _hw, hh) => {
            const rect = { x: tx - hx, y: ty - hy, w: tw, h: th + (TOUR[tour].extraH ?? 0) };
            const visibleH = Math.min(rect.h, 220);
            if (rect.y < 64 || rect.y + visibleH > hh - 80) {
              scrollRef.current?.scrollTo({
                y: Math.max(0, scrollYRef.current + rect.y - 130),
                animated: true,
              });
              setTimeout(
                () =>
                  target.measureInWindow((tx2, ty2, tw2, th2) =>
                    host.measureInWindow((hx2, hy2) =>
                      setTourRect({ x: tx2 - hx2, y: ty2 - hy2, w: tw2, h: th2 + (TOUR[tour].extraH ?? 0) })
                    )
                  ),
                380
              );
            } else {
              setTourRect(rect);
            }
          });
        });
      apply();
    }, 260);
    return () => clearTimeout(timer);
  }, [tour, editing, editIndex, favorites]);

  // 투어 진행: 사용자의 실제 행동을 감지해 다음 단계로
  useEffect(() => {
    if (tour === 1 && editing) setTour(2);
    if (tour === 6 && !editing) setTour(7);
  }, [editing, tour]);
  useEffect(() => {
    if (tour === 3 && editIndex != null) setTour(4);
  }, [editIndex, tour]);

  useEffect(() => {
    // 첫 시도 실패 시 콜드 스타트(서버 깨우기)로 보고 최대 75초 재시도
    checkHealth().then((up) => {
      if (up) {
        setBackendUp(true);
      } else {
        setBackendUp(null); // '깨우는 중' 상태 유지
        waitForBackend().then(setBackendUp);
      }
    });
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
      <View ref={rootRef} style={styles.safe} collapsable={false}>
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        scrollEnabled={tour == null}
        scrollEventThrottle={32}
        onScroll={(e) => {
          scrollYRef.current = e.nativeEvent.contentOffset.y;
        }}
      >
        {/* 상단 설정 · 사용법 버튼 */}
        <View style={styles.topBar}>
          <Pressable
            style={styles.settingsBtn}
            onPress={() => navigation.navigate('Settings')}
            accessibilityRole="button"
            accessibilityLabel="설정"
          >
            <Text style={styles.settingsText}>⚙️ 설정</Text>
          </Pressable>
          <Pressable
            style={styles.settingsBtn}
            onPress={() => setTour(0)}
            accessibilityRole="button"
            accessibilityLabel="사용법 안내 보기"
          >
            <Text style={styles.settingsText}>❓ 사용법</Text>
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
        {backendUp === null && (
          <View style={styles.waking}>
            <Text style={styles.wakingText}>
              서버에 연결하는 중입니다… 첫 접속은 최대 1분 정도 걸릴 수 있어요.
            </Text>
          </View>
        )}
        {backendUp === false && (
          <View style={styles.warn}>
            <Text style={styles.warnText}>
              서버에 연결할 수 없습니다. 잠시 후 새로고침해 주세요.
            </Text>
          </View>
        )}

        {/* 자주 가는 곳 */}
        <View style={styles.favHeader}>
          <Text style={styles.sectionTitle}>⭐ 자주 가는 곳</Text>
          <View ref={editToggleRef} collapsable={false}>
            <Pressable
              style={styles.editBtn}
              onPress={() => {
                setEditing((v) => !v);
                setEditIndex(null);
              }}
              accessibilityRole="button"
              accessibilityLabel={editing ? '편집 완료' : '자주 가는 곳 편집'}
            >
              <Text style={styles.editText}>{editing ? '완료' : '✏️ 편집'}</Text>
            </Pressable>
          </View>
        </View>

        {editing && (
          <View ref={formRef} collapsable={false}>
            <AddFavoriteForm
              initial={editIndex != null ? favorites[editIndex] : null}
              onCancel={() => setEditIndex(null)}
              onAdd={(place) => {
                if (editIndex != null) {
                  updateFavorite(editIndex, place);
                  setEditIndex(null);
                  if (tour === 4) setTour(5);
                } else {
                  addFavorite(place);
                  if (tour === 2) setTour(3);
                }
              }}
            />
          </View>
        )}

        {editing ? (
          <View ref={gridRef} collapsable={false}>
            <Text style={styles.dragGuide}>
              카드를 길게 눌러 끌면 순서를 바꾸고, ✏️로 수정할 수 있어요
            </Text>
            <DraggableFavoriteGrid
              items={favorites}
              onReorder={reorderFavorites}
              onDelete={(i) => {
                removeFavorite(i);
                setEditIndex(null);
                if (tour === 5) setTour(6);
              }}
              onEdit={setEditIndex}
            />
          </View>
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
        <View ref={searchRef} collapsable={false}>
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
        </View>

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

      {/* 인터랙티브 사용법 투어 (실제 버튼을 짚어주고 직접 누르며 진행) */}
      {tour != null && (
        <CoachMark
          visible
          rect={TOUR[tour].target ? tourRect : null}
          title={TOUR[tour].title}
          text={TOUR[tour].text}
          step={tour}
          total={TOUR.length}
          onSkip={() => setTour(null)}
          actionLabel={TOUR[tour].action}
          onAction={
            TOUR[tour].action
              ? () => (tour === 0 ? setTour(1) : setTour(null))
              : undefined
          }
        />
      )}
      </View>
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
  topBar: { flexDirection: 'row', justifyContent: 'space-between' },
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
  waking: {
    backgroundColor: '#FFF8E1',
    borderRadius: sizes.radiusSm,
    padding: 12,
    marginBottom: 12,
  },
  wakingText: { color: '#8A6D00', fontSize: sizes.fontSmall },
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
