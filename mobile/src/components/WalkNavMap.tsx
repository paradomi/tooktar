/** 도보 네비게이션 지도 — 도보 경로 폴리라인 + 실시간 내 위치 추적 (네이버 도보내비 스타일).
 *  RouteMap 과 달리 GPS 갱신 시 지도를 다시 그리지 않고 마커만 이동 + 지도 자동 추적(panTo).
 *  웹: div 직접 렌더 / 네이티브: WebView + injectJavaScript 로 위치만 주입.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import { colors, sizes } from '../theme';
import { loadKakaoSdk } from '../utils/kakaoSdk';

export interface NavCoord {
  lat: number;
  lng: number;
}

interface Props {
  kakaoKey: string;
  /** 도보 경로 좌표 (Tmap walkRouteDetail coords) */
  coords: NavCoord[];
  /** 실시간 내 위치 */
  myPos: NavCoord | null;
  /** 도착 지점 (정류장/역/목적지) */
  endLat: number;
  endLng: number;
  endLabel?: string;
  height?: number;
}

const WALK_COLOR = '#7B1FA2';
const NAV_LEVEL = 3; // 추적 시 줌 레벨 (도보용 근접)

const MY_DOT_HTML =
  '<div style="width:22px;height:22px;background:#4285F4;border:3px solid #fff;border-radius:50%;' +
  'box-shadow:0 0 0 4px rgba(66,133,244,0.35),0 1px 4px rgba(0,0,0,0.4);"></div>';

function escapeHtml(s: string): string {
  return (s || '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string)
  );
}

/** 웹: 지도 1회 생성 후 위치 갱신은 마커 이동 + panTo 만 수행 */
function WebNavMap({ kakaoKey, coords, myPos, endLat, endLng, endLabel, height, follow }:
  Props & { height: number; follow: boolean }) {
  const divRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const dotRef = useRef<any>(null);
  const kakaoRef = useRef<any>(null);

  // 지도 + 경로선은 coords 가 바뀔 때만 새로 그림
  useEffect(() => {
    let cancelled = false;
    if (!divRef.current) return;
    const el = divRef.current;
    el.innerHTML = '';
    mapRef.current = null;
    dotRef.current = null;
    loadKakaoSdk(kakaoKey)
      .then((kakao) => {
        if (cancelled || !divRef.current) return;
        kakaoRef.current = kakao;
        const center = coords.length
          ? new kakao.maps.LatLng(coords[0].lat, coords[0].lng)
          : new kakao.maps.LatLng(endLat, endLng);
        const map = new kakao.maps.Map(divRef.current, { center, level: NAV_LEVEL });
        mapRef.current = map;
        const bounds = new kakao.maps.LatLngBounds();
        const path = coords.map((c) => {
          const ll = new kakao.maps.LatLng(c.lat, c.lng);
          bounds.extend(ll);
          return ll;
        });
        if (path.length > 1) {
          new kakao.maps.Polyline({
            map, path, strokeWeight: 7, strokeColor: WALK_COLOR, strokeOpacity: 0.9, strokeStyle: 'solid',
          });
        }
        const endLL = new kakao.maps.LatLng(endLat, endLng);
        bounds.extend(endLL);
        new kakao.maps.CustomOverlay({
          map, position: endLL, yAnchor: 1, zIndex: 4,
          content: `<div style="padding:4px 8px;background:#d32f2f;color:#fff;font-size:12px;font-weight:bold;border-radius:6px;white-space:nowrap;font-family:sans-serif;">🏁 ${endLabel || '도착'}</div>`,
        });
        if (!bounds.isEmpty()) map.setBounds(bounds, 28, 28, 28, 28);
      })
      .catch(() => {
        if (divRef.current)
          divRef.current.innerHTML =
            '<div style="padding:12px;color:#b00;font-family:sans-serif;font-size:13px;">지도를 불러올 수 없습니다.</div>';
      });
    return () => { cancelled = true; };
  }, [kakaoKey, coords, endLat, endLng, endLabel]);

  // 위치 갱신: 마커만 이동, 추적 켜져 있으면 지도 따라감
  useEffect(() => {
    const kakao = kakaoRef.current;
    const map = mapRef.current;
    if (!kakao || !map || !myPos) return;
    const ll = new kakao.maps.LatLng(myPos.lat, myPos.lng);
    if (!dotRef.current) {
      dotRef.current = new kakao.maps.CustomOverlay({
        map, position: ll, zIndex: 9, content: MY_DOT_HTML,
      });
    } else {
      dotRef.current.setPosition(ll);
    }
    if (follow) {
      map.setLevel(NAV_LEVEL);
      map.panTo(ll);
    }
  }, [myPos, follow]);

  return React.createElement('div', {
    ref: divRef,
    style: { width: '100%', height, borderRadius: sizes.radius, overflow: 'hidden', background: '#dde' },
  });
}

/** 네이티브(WebView) HTML — window.updatePos 로 위치만 주입받음 */
function buildNavHtml(
  kakaoKey: string,
  coords: NavCoord[],
  endLat: number,
  endLng: number,
  endLabel: string
): string {
  const coordsJson = JSON.stringify(coords);
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoKey}&autoload=false"></script>
<style>*{margin:0;padding:0}html,body,#map{width:100%;height:100%}</style>
</head>
<body>
<div id="map"></div>
<script>
  var map = null, dot = null, follow = true;
  window.updatePos = function(lat, lng) {
    if (!map || !window.kakao) return;
    var ll = new kakao.maps.LatLng(lat, lng);
    if (!dot) {
      dot = new kakao.maps.CustomOverlay({
        map: map, position: ll, zIndex: 9,
        content: '${MY_DOT_HTML.replace(/'/g, "\\'")}'
      });
    } else { dot.setPosition(ll); }
    if (follow) { map.setLevel(${NAV_LEVEL}); map.panTo(ll); }
  };
  window.setFollow = function(v) { follow = !!v; };
  if (window.kakao && window.kakao.maps) {
    kakao.maps.load(function() {
      var coords = ${coordsJson};
      var center = coords.length
        ? new kakao.maps.LatLng(coords[0].lat, coords[0].lng)
        : new kakao.maps.LatLng(${endLat}, ${endLng});
      map = new kakao.maps.Map(document.getElementById('map'), { center: center, level: ${NAV_LEVEL} });
      var bounds = new kakao.maps.LatLngBounds();
      var path = coords.map(function(c){
        var ll = new kakao.maps.LatLng(c.lat, c.lng);
        bounds.extend(ll);
        return ll;
      });
      if (path.length > 1) {
        new kakao.maps.Polyline({
          map: map, path: path, strokeWeight: 7,
          strokeColor: '${WALK_COLOR}', strokeOpacity: 0.9, strokeStyle: 'solid'
        });
      }
      var endLL = new kakao.maps.LatLng(${endLat}, ${endLng});
      bounds.extend(endLL);
      new kakao.maps.CustomOverlay({
        map: map, position: endLL, yAnchor: 1, zIndex: 4,
        content: '<div style="padding:4px 8px;background:#d32f2f;color:#fff;font-size:12px;'+
                 'font-weight:bold;border-radius:6px;white-space:nowrap;font-family:sans-serif;">'+
                 '🏁 ${escapeHtml(endLabel)}</div>'
      });
      if (!bounds.isEmpty()) map.setBounds(bounds, 28, 28, 28, 28);
      // 지도 손으로 움직이면 추적 일시 해제 (RN 쪽 버튼으로 재개)
      kakao.maps.event.addListener(map, 'dragstart', function(){ follow = false; });
    });
  }
</script>
</body>
</html>`;
}

export default function WalkNavMap({
  kakaoKey,
  coords,
  myPos,
  endLat,
  endLng,
  endLabel = '도착',
  height = 260,
}: Props) {
  const [follow, setFollow] = useState(true);
  const webviewRef = useRef<WebView | null>(null);

  const html = useMemo(
    () => buildNavHtml(kakaoKey, coords, endLat, endLng, endLabel),
    [kakaoKey, coords, endLat, endLng, endLabel]
  );

  // 네이티브: GPS 갱신 시 JS 주입으로 마커만 이동
  useEffect(() => {
    if (Platform.OS === 'web' || !myPos) return;
    webviewRef.current?.injectJavaScript(
      `window.updatePos && window.updatePos(${myPos.lat}, ${myPos.lng}); true;`
    );
  }, [myPos]);

  // 네이티브: 추적 토글 주입
  useEffect(() => {
    if (Platform.OS === 'web') return;
    webviewRef.current?.injectJavaScript(`window.setFollow && window.setFollow(${follow}); true;`);
  }, [follow]);

  if (!kakaoKey) return null;

  return (
    <View style={[styles.wrap, { height }]}>
      {Platform.OS === 'web' ? (
        <WebNavMap
          kakaoKey={kakaoKey}
          coords={coords}
          myPos={myPos}
          endLat={endLat}
          endLng={endLng}
          endLabel={endLabel}
          height={height}
          follow={follow}
        />
      ) : (
        <WebView
          ref={webviewRef}
          originWhitelist={['*']}
          source={{ html, baseUrl: 'https://localhost' }}
          style={styles.webview}
          javaScriptEnabled
          domStorageEnabled
        />
      )}
      {/* 내 위치 추적 토글 */}
      <Pressable
        style={[styles.followBtn, follow && styles.followOn]}
        onPress={() => setFollow((v) => !v)}
        accessibilityRole="button"
        accessibilityLabel={follow ? '위치 추적 끄기' : '내 위치로 따라가기'}
      >
        <Text style={[styles.followIcon, follow && styles.followIconOn]}>◎</Text>
      </Pressable>
      {!myPos && (
        <View style={styles.waitBadge}>
          <Text style={styles.waitText}>GPS 위치 찾는 중…</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    borderRadius: sizes.radius,
    overflow: 'hidden',
    backgroundColor: '#dde',
    marginTop: 14,
  },
  webview: { flex: 1, backgroundColor: 'transparent' },
  followBtn: {
    position: 'absolute',
    right: 10,
    bottom: 10,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 3,
  },
  followOn: { backgroundColor: '#4285F4', borderColor: '#4285F4' },
  followIcon: { fontSize: 22, color: colors.gray, fontWeight: '700' },
  followIconOn: { color: '#fff' },
  waitBadge: {
    position: 'absolute',
    top: 10,
    alignSelf: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  waitText: { color: '#fff', fontSize: 13, fontWeight: '600' },
});
