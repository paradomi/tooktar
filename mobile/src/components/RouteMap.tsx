/** 경로 지도 — 카카오맵 SDK로 ODsay lane 폴리라인 + 도보 + 출발/도착·현재위치 마커 렌더.
 *
 *  렌더 방식(플랫폼별):
 *   - 웹(Expo web): 부모 페이지 div 에 카카오 SDK 를 직접 로드 (iframe 미사용 —
 *     srcdoc iframe 은 origin 이 null 이라 카카오 도메인 검증을 통과 못 하기 때문).
 *   - 네이티브(iOS/Android): react-native-webview 에 HTML(buildHtml) 주입.
 *     RN 은 브라우저가 아니라 카카오맵 JS SDK 를 띄울 방법이 WebView 뿐.
 *
 *  주의: 카카오맵 JS SDK는 [내 애플리케이션 > 플랫폼 > Web]에 등록된 도메인에서만 동작.
 *   - 웹: 실제 접속 origin(예: http://localhost:8082) 등록
 *   - 네이티브 WebView: baseUrl(https://localhost) 등록
 */
import React, { useMemo, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import { colors, sizes } from '../theme';
import { TRANSIT_COLORS, transitColor, type LaneData, type Coord } from '../api/client';
import { loadKakaoSdk } from '../utils/kakaoSdk';

/** lane 순서와 1:1 매칭되는 대중교통 구간 정보 */
export interface TransitInfo {
  kind: 'bus' | 'subway';
  busType?: number;
}
/** 지도에 찍을 노선 라벨 마커 (예: "5번", "수인분당선") */
export interface TransitLabel {
  lat: number;
  lng: number;
  label: string;
  color: string;
}

/** 웹: 부모 origin(localhost:포트)에서 카카오 SDK 로드 후 div 에 직접 지도 렌더.
 *  iframe srcdoc 은 origin 이 null 이라 카카오 도메인 검증을 통과 못 함 → 직접 렌더로 해결.
 */
// SDK 로더는 utils/kakaoSdk 로 공유 (RoadView 등과 단일 인스턴스)

function renderKakaoMap(
  kakao: any,
  el: HTMLElement,
  sections: { coords: { lat: number; lng: number }[]; color: string }[],
  origin: Coord,
  dest: Coord,
  myLocation?: { lat: number; lng: number } | null,
  walkLines?: { lat: number; lng: number }[][],
  transferPoints?: { lat: number; lng: number }[],
  transitLabels?: TransitLabel[]
) {
  const centerLat = (origin.lat + dest.lat) / 2;
  const centerLng = (origin.lng + dest.lng) / 2;
  const map = new kakao.maps.Map(el, {
    center: new kakao.maps.LatLng(centerLat, centerLng),
    level: 6,
    mapTypeId: kakao.maps.MapTypeId.ROADMAP, // 기본 일반지도 (위성은 우상단 토글)
  });
  map.addControl(new kakao.maps.MapTypeControl(), kakao.maps.ControlPosition.TOPRIGHT);
  map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
  const bounds = new kakao.maps.LatLngBounds();

  sections.forEach((sec) => {
    const path = sec.coords.map((c) => {
      const ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    });
    if (path.length > 1) {
      new kakao.maps.Polyline({
        map, path, strokeWeight: 6, strokeColor: sec.color, strokeOpacity: 0.9, strokeStyle: 'solid',
      });
    }
  });

  (walkLines || []).forEach((w) => {
    if (!w || w.length < 2) return;
    const path = w.map((c) => {
      const ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    });
    new kakao.maps.Polyline({
      map, path, strokeWeight: 5, strokeColor: '#7B1FA2', strokeOpacity: 0.9, strokeStyle: 'shortdash',
    });
  });

  const marker = (lat: number, lng: number, text: string, color: string) => {
    const ll = new kakao.maps.LatLng(lat, lng);
    bounds.extend(ll);
    new kakao.maps.CustomOverlay({
      map, position: ll, yAnchor: 1,
      content: `<div style="padding:4px 8px;background:${color};color:#fff;font-size:12px;font-weight:bold;border-radius:6px;white-space:nowrap;font-family:sans-serif;">${text}</div>`,
    });
  };
  marker(origin.lat, origin.lng, `🚩 ${origin.name}`, '#1565c0');
  marker(dest.lat, dest.lng, `🏁 ${dest.name}`, '#d32f2f');

  // 환승 지점 🔄 마커
  (transferPoints || []).forEach((tp) => {
    const ll = new kakao.maps.LatLng(tp.lat, tp.lng);
    new kakao.maps.CustomOverlay({
      map, position: ll, yAnchor: 0.5, zIndex: 4,
      content:
        '<div style="width:24px;height:24px;line-height:24px;text-align:center;background:#fff;border:2px solid #7B1FA2;border-radius:50%;font-size:13px;box-shadow:0 1px 3px rgba(0,0,0,0.3);">🔄</div>',
    });
  });

  // 노선 라벨 마커 (어떤 버스/노선을 타는지)
  (transitLabels || []).forEach((tl) => {
    const ll = new kakao.maps.LatLng(tl.lat, tl.lng);
    bounds.extend(ll);
    new kakao.maps.CustomOverlay({
      map, position: ll, yAnchor: 1.4, zIndex: 6,
      content:
        `<div style="display:flex;align-items:center;gap:4px;padding:3px 8px;background:${tl.color};color:#fff;font-size:13px;font-weight:bold;border-radius:12px;white-space:nowrap;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);font-family:sans-serif;">${tl.label}</div>`,
    });
  });

  if (myLocation) {
    const ll = new kakao.maps.LatLng(myLocation.lat, myLocation.lng);
    new kakao.maps.CustomOverlay({
      map, position: ll, zIndex: 5,
      content:
        '<div style="width:18px;height:18px;background:#4285F4;border:3px solid #fff;border-radius:50%;box-shadow:0 0 0 2px rgba(66,133,244,0.4),0 1px 4px rgba(0,0,0,0.4);"></div>',
    });
  }

  if (!bounds.isEmpty()) map.setBounds(bounds, 24, 24, 24, 24);
}

/** 웹 전용 지도 컴포넌트 */
function WebMap({
  kakaoKey,
  lane,
  origin,
  dest,
  myLocation,
  walkLines,
  transferPoints,
  transit,
  transitLabels,
  height,
}: Props & { height: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    let cancelled = false;
    if (!ref.current) return;
    const el = ref.current;
    el.innerHTML = '';
    loadKakaoSdk(kakaoKey)
      .then((kakao) => {
        if (cancelled || !ref.current) return;
        renderKakaoMap(
          kakao,
          ref.current,
          buildSections(lane, transit),
          origin,
          dest,
          myLocation,
          walkLines,
          transferPoints,
          transitLabels
        );
      })
      .catch(() => {
        if (ref.current) ref.current.innerHTML =
          '<div style="padding:12px;color:#b00;font-family:sans-serif;font-size:13px;">지도를 불러올 수 없습니다. 카카오 콘솔에 ' +
          window.location.origin + ' 도메인을 등록하세요.</div>';
      });
    return () => { cancelled = true; };
  }, [kakaoKey, lane, origin, dest, myLocation, walkLines, transferPoints, transit, transitLabels]);

  return React.createElement('div', {
    ref,
    style: { width: '100%', height, borderRadius: sizes.radius, overflow: 'hidden', background: '#dde' },
  });
}

interface Props {
  kakaoKey: string;
  lane: LaneData | null;
  origin: Coord;
  dest: Coord;
  height?: number;
  /** 현재 위치(GPS) — 있으면 파란 점 마커 표시 */
  myLocation?: { lat: number; lng: number } | null;
  /** 도보 구간 폴리라인들 (Tmap 보행경로) — 보라 점선 */
  walkLines?: { lat: number; lng: number }[][];
  /** 환승 지점 — 🔄 마커 */
  transferPoints?: { lat: number; lng: number }[];
  /** lane 순서와 매칭되는 대중교통 종류 (색상 정밀화용) */
  transit?: TransitInfo[];
  /** 노선 라벨 마커 (어떤 버스/노선을 타는지) */
  transitLabels?: TransitLabel[];
}

interface LatLng {
  lat: number;
  lng: number;
}

/** lane → [{coords, color}] 폴리라인 섹션 */
function buildSections(
  lane: LaneData | null,
  transit?: TransitInfo[]
): { coords: LatLng[]; color: string }[] {
  const out: { coords: LatLng[]; color: string }[] = [];
  if (!lane?.lane) return out;
  // lane[] 는 도보를 제외한 대중교통 구간이 여정 순서대로 들어옴 → transit step 과 1:1 매칭해 색 결정
  lane.lane.forEach((l, i) => {
    const cls = l.class ?? 0;
    const t = transit?.[i];
    // 매칭되면 정확한 종류색, 아니면 class 기반 fallback (1=지하철, 2=버스)
    const color = t
      ? transitColor(t.kind, t.busType)
      : cls === 1
        ? TRANSIT_COLORS.subway
        : cls === 2
          ? TRANSIT_COLORS.busGeneral
          : '#999999';
    for (const sec of l.section ?? []) {
      const coords: LatLng[] = [];
      for (const pt of sec.graphPos ?? []) {
        if (typeof pt.x === 'number' && typeof pt.y === 'number') {
          coords.push({ lat: pt.y, lng: pt.x });
        }
      }
      if (coords.length) out.push({ coords, color });
    }
  });
  return out;
}

/** 네이티브(WebView) 전용 — 카카오맵 HTML 문자열 생성. (웹은 WebMap 이 div 직접 렌더) */
function buildHtml(
  kakaoKey: string,
  sections: any[],
  origin: Coord,
  dest: Coord,
  myLocation?: { lat: number; lng: number } | null,
  walkLines?: { lat: number; lng: number }[][],
  transferPoints?: { lat: number; lng: number }[],
  transitLabels?: TransitLabel[]
): string {
  const centerLat = (origin.lat + dest.lat) / 2;
  const centerLng = (origin.lng + dest.lng) / 2;
  const sectionsJson = JSON.stringify(sections);
  const myLoc = myLocation ? JSON.stringify(myLocation) : 'null';
  const walksJson = JSON.stringify((walkLines || []).filter((w) => w && w.length > 1));
  const transfersJson = JSON.stringify(transferPoints || []);
  const labelsJson = JSON.stringify(transitLabels || []);

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoKey}&autoload=false"></script>
<style>
  * { margin:0; padding:0; }
  html,body,#map { width:100%; height:100%; }
  #err { position:absolute; top:0; left:0; right:0; padding:12px;
         font-family:sans-serif; font-size:14px; color:#b00; background:#fee; display:none; }
</style>
</head>
<body>
<div id="map"></div>
<div id="err"></div>
<script>
  function showErr(){
    var d = document.getElementById('err');
    d.innerHTML = '지도를 불러올 수 없습니다.<br>카카오 개발자 콘솔 > 플랫폼 > Web 에 아래 도메인을 등록하세요:<br><b>' +
      window.location.origin + '</b>';
    d.style.display = 'block';
  }
  if (!window.kakao || !window.kakao.maps) {
    showErr();
  } else {
    kakao.maps.load(function() {
      try {
        var map = new kakao.maps.Map(document.getElementById('map'), {
          center: new kakao.maps.LatLng(${centerLat}, ${centerLng}),
          level: 6,
          mapTypeId: kakao.maps.MapTypeId.ROADMAP
        });
        // 일반/위성(스카이뷰) 토글 + 줌 컨트롤
        map.addControl(new kakao.maps.MapTypeControl(), kakao.maps.ControlPosition.TOPRIGHT);
        map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);
        var bounds = new kakao.maps.LatLngBounds();

        var sections = ${sectionsJson};
        sections.forEach(function(sec) {
          var path = sec.coords.map(function(c){
            var ll = new kakao.maps.LatLng(c.lat, c.lng);
            bounds.extend(ll);
            return ll;
          });
          if (path.length > 1) {
            new kakao.maps.Polyline({
              map: map, path: path, strokeWeight: 6,
              strokeColor: sec.color, strokeOpacity: 0.9, strokeStyle: 'solid'
            });
          }
        });

        // 도보 구간 — 보라색 점선 (Tmap 보행경로)
        var walks = ${walksJson};
        walks.forEach(function(w) {
          var path = w.map(function(c){
            var ll = new kakao.maps.LatLng(c.lat, c.lng);
            bounds.extend(ll);
            return ll;
          });
          if (path.length > 1) {
            new kakao.maps.Polyline({
              map: map, path: path, strokeWeight: 5,
              strokeColor: '#7B1FA2', strokeOpacity: 0.9, strokeStyle: 'shortdash'
            });
          }
        });

        function marker(lat, lng, text, color) {
          var ll = new kakao.maps.LatLng(lat, lng);
          bounds.extend(ll);
          new kakao.maps.CustomOverlay({
            map: map, position: ll, yAnchor: 1,
            content: '<div style="padding:4px 8px;background:'+color+';color:#fff;'+
                     'font-size:12px;font-weight:bold;border-radius:6px;white-space:nowrap;'+
                     'font-family:sans-serif;">'+text+'</div>'
          });
        }
        marker(${origin.lat}, ${origin.lng}, '🚩 ${escapeHtml(origin.name)}', '#1565c0');
        marker(${dest.lat}, ${dest.lng}, '🏁 ${escapeHtml(dest.name)}', '#d32f2f');

        // 환승 지점 🔄 마커
        var transfers = ${transfersJson};
        transfers.forEach(function(tp) {
          new kakao.maps.CustomOverlay({
            map: map, position: new kakao.maps.LatLng(tp.lat, tp.lng), yAnchor: 0.5, zIndex: 4,
            content: '<div style="width:24px;height:24px;line-height:24px;text-align:center;'+
                     'background:#fff;border:2px solid #7B1FA2;border-radius:50%;font-size:13px;'+
                     'box-shadow:0 1px 3px rgba(0,0,0,0.3);">🔄</div>'
          });
        });

        // 노선 라벨 마커 (어떤 버스/노선을 타는지)
        var labels = ${labelsJson};
        labels.forEach(function(tl) {
          new kakao.maps.CustomOverlay({
            map: map, position: new kakao.maps.LatLng(tl.lat, tl.lng), yAnchor: 1.4, zIndex: 6,
            content: '<div style="padding:3px 8px;color:#fff;font-size:13px;font-weight:bold;'+
                     'border-radius:12px;white-space:nowrap;border:2px solid #fff;'+
                     'box-shadow:0 1px 4px rgba(0,0,0,0.4);font-family:sans-serif;background:'+tl.color+';">'+tl.label+'</div>'
          });
        });

        // 현재 위치 — 파란 점 (Google Maps 스타일)
        var myLoc = ${myLoc};
        if (myLoc && typeof myLoc.lat === 'number' && typeof myLoc.lng === 'number') {
          var myLL = new kakao.maps.LatLng(myLoc.lat, myLoc.lng);
          new kakao.maps.CustomOverlay({
            map: map, position: myLL, zIndex: 5,
            content: '<div style="width:18px;height:18px;background:#4285F4;border:3px solid #fff;'+
                     'border-radius:50%;box-shadow:0 0 0 2px rgba(66,133,244,0.4),0 1px 4px rgba(0,0,0,0.4);"></div>'
          });
        }

        if (!bounds.isEmpty()) map.setBounds(bounds, 24, 24, 24, 24);
      } catch (e) {
        showErr();
      }
    });
  }
</script>
</body>
</html>`;
}

function escapeHtml(s: string): string {
  return (s || '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string)
  );
}

export default function RouteMap({
  kakaoKey,
  lane,
  origin,
  dest,
  height = 300,
  myLocation,
  walkLines,
  transferPoints,
  transit,
  transitLabels,
}: Props) {
  const html = useMemo(
    () =>
      buildHtml(
        kakaoKey,
        buildSections(lane, transit),
        origin,
        dest,
        myLocation,
        walkLines,
        transferPoints,
        transitLabels
      ),
    [kakaoKey, lane, origin, dest, myLocation, walkLines, transferPoints, transit, transitLabels]
  );

  if (!kakaoKey) {
    return (
      <View style={[styles.fallback, { height }]}>
        <Text style={styles.fallbackText}>지도 키를 불러오지 못했습니다</Text>
      </View>
    );
  }

  // 웹: 부모 origin 으로 카카오 SDK 직접 로드 (iframe srcdoc 의 origin=null 문제 회피)
  if (Platform.OS === 'web') {
    return (
      <View style={[styles.wrap, { height }]}>
        <WebMap
          kakaoKey={kakaoKey}
          lane={lane}
          origin={origin}
          dest={dest}
          myLocation={myLocation}
          walkLines={walkLines}
          transferPoints={transferPoints}
          transit={transit}
          transitLabels={transitLabels}
          height={height}
        />
      </View>
    );
  }

  return (
    <View style={[styles.wrap, { height }]}>
      <WebView
        originWhitelist={['*']}
        source={{ html, baseUrl: 'https://localhost' }}
        style={styles.webview}
        javaScriptEnabled
        domStorageEnabled
        scrollEnabled={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    borderRadius: sizes.radius,
    overflow: 'hidden',
    backgroundColor: '#dde',
  },
  webview: { flex: 1, backgroundColor: 'transparent' },
  fallback: {
    width: '100%',
    borderRadius: sizes.radius,
    backgroundColor: '#e8edf2',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fallbackText: { color: colors.gray, fontSize: sizes.fontSmall },
});
