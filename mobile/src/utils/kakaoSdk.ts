/** 카카오맵 JS SDK 로더 (웹 전용) — 모듈 레벨 단일 Promise 캐싱으로 다중 마운트 race 방지 */
let _kakaoSdkPromise: Promise<any> | null = null;

export function loadKakaoSdk(key: string): Promise<any> {
  const w = window as any;
  if (w.kakao && w.kakao.maps) return Promise.resolve(w.kakao);
  if (_kakaoSdkPromise) return _kakaoSdkPromise;

  _kakaoSdkPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById('kakao-sdk') as HTMLScriptElement | null;
    const onReady = () => w.kakao.maps.load(() => resolve(w.kakao));
    if (existing) {
      if (w.kakao && w.kakao.maps) onReady();
      else existing.addEventListener('load', onReady, { once: true });
      return;
    }
    const s = document.createElement('script');
    s.id = 'kakao-sdk';
    s.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${key}&autoload=false`;
    s.onload = onReady;
    s.onerror = () => {
      _kakaoSdkPromise = null; // 실패 시 재시도 가능하게
      reject(new Error('kakao sdk load failed'));
    };
    document.head.appendChild(s);
  });
  return _kakaoSdkPromise;
}
