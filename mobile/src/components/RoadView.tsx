/** 카카오 로드뷰(거리뷰) — 좌표 기준 파노라마. 웹은 div 직접 렌더, 네이티브는 WebView. */
import React, { useEffect, useRef } from 'react';
import { View, Text, Platform, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import { loadKakaoSdk } from '../utils/kakaoSdk';
import { colors } from '../theme';

interface Props {
  kakaoKey: string;
  lat: number;
  lng: number;
  height?: number;
}

/** 웹 전용 — kakao.maps.Roadview + RoadviewClient 로 가장 가까운 파노라마 표시 */
function WebRoadView({ kakaoKey, lat, lng, height }: Props & { height: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    let cancelled = false;
    if (!ref.current) return;
    const el = ref.current;
    el.innerHTML = '';
    loadKakaoSdk(kakaoKey)
      .then((kakao) => {
        if (cancelled || !ref.current) return;
        const rv = new kakao.maps.Roadview(ref.current);
        const client = new kakao.maps.RoadviewClient();
        const pos = new kakao.maps.LatLng(lat, lng);
        client.getNearestPanoId(pos, 50, (panoId: number | null) => {
          if (cancelled) return;
          if (panoId) rv.setPanoId(panoId, pos);
          else if (ref.current)
            ref.current.innerHTML =
              '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#888;font-family:sans-serif;font-size:14px;">이 지점은 거리뷰가 없습니다</div>';
        });
      })
      .catch(() => {
        if (ref.current)
          ref.current.innerHTML =
            '<div style="padding:12px;color:#b00;font-family:sans-serif;font-size:13px;">거리뷰를 불러올 수 없습니다.</div>';
      });
    return () => {
      cancelled = true;
    };
  }, [kakaoKey, lat, lng]);

  return React.createElement('div', {
    ref,
    style: { width: '100%', height, background: '#222' },
  });
}

/** 네이티브 전용 — WebView 로 로드뷰 HTML 렌더 */
function buildRoadViewHtml(kakaoKey: string, lat: number, lng: number): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoKey}&autoload=false"></script>
<style>*{margin:0;padding:0}html,body,#rv{width:100%;height:100%}
#msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#888;font-family:sans-serif;font-size:14px}</style>
</head><body>
<div id="rv"></div><div id="msg" style="display:none">이 지점은 거리뷰가 없습니다</div>
<script>
kakao.maps.load(function(){
  var pos = new kakao.maps.LatLng(${lat}, ${lng});
  var rv = new kakao.maps.Roadview(document.getElementById('rv'));
  var client = new kakao.maps.RoadviewClient();
  client.getNearestPanoId(pos, 50, function(panoId){
    if (panoId) rv.setPanoId(panoId, pos);
    else { document.getElementById('rv').style.display='none'; document.getElementById('msg').style.display='flex'; }
  });
});
</script></body></html>`;
}

export default function RoadView({ kakaoKey, lat, lng, height = 320 }: Props) {
  if (!kakaoKey) {
    return (
      <View style={[styles.fallback, { height }]}>
        <Text style={styles.fallbackText}>지도 키를 불러오지 못했습니다</Text>
      </View>
    );
  }
  if (Platform.OS === 'web') {
    return (
      <View style={{ height }}>
        <WebRoadView kakaoKey={kakaoKey} lat={lat} lng={lng} height={height} />
      </View>
    );
  }
  return (
    <View style={{ height }}>
      <WebView
        originWhitelist={['*']}
        source={{ html: buildRoadViewHtml(kakaoKey, lat, lng), baseUrl: 'https://localhost' }}
        style={{ flex: 1 }}
        javaScriptEnabled
        domStorageEnabled
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fallback: { alignItems: 'center', justifyContent: 'center', backgroundColor: colors.light },
  fallbackText: { color: colors.gray, fontSize: 14 },
});
