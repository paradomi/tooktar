/** 전역 글자 배율 — Text/TextInput 의 forwardRef 렌더 함수를 패치해,
 *  렌더 입력 props 의 fontSize 에 배율을 곱한 뒤 원본 렌더에 넘긴다.
 *
 *  핵심: 출력 element 를 건드리지 않는다(웹에선 이미 DOM 으로 변환돼 스타일 머지가 안 먹음).
 *  입력 props.style 에 scaled fontSize 를 얹으면 RN(네이티브)·react-native-web 모두 올바르게 처리.
 *  실제 리렌더는 App 이 scale 을 Navigator key 로 사용해 트리거한다.
 */
import { Text, TextInput, StyleSheet } from 'react-native';

let currentScale = 1;
export function setGlobalFontScale(s: number) {
  currentScale = s;
}
export function getGlobalFontScale() {
  return currentScale;
}

// Gowun Batang(고운 바탕) 폰트 — 로드 완료 후 전역 적용
let fontReady = false;
export function setFontReady(v: boolean) {
  fontReady = v;
}
const REGULAR = 'GowunBatang_400Regular';
const BOLD = 'GowunBatang_700Bold';

/** fontWeight 가 굵으면 Bold, 아니면 Regular family 매핑 */
function pickFamily(weight: any): string {
  const w = String(weight ?? '');
  return w === 'bold' || w === '600' || w === '700' || w === '800' || w === '900' ? BOLD : REGULAR;
}

function scaleProps(props: any) {
  if (!props) return props;
  const flat = (StyleSheet.flatten(props.style) || {}) as {
    fontSize?: number;
    lineHeight?: number;
    fontWeight?: any;
    fontFamily?: string;
  };
  const fixed = props.allowFontScaling === false; // 로고 등 크기 고정
  const needScale = currentScale !== 1 && !fixed;
  // 이미 fontFamily 가 지정된 경우(아이콘 폰트 등)는 건드리지 않음
  const needFont = fontReady && !flat.fontFamily;
  if (!needScale && !needFont) return props;

  const extra: any = {};
  if (needScale) {
    const baseFs = typeof flat.fontSize === 'number' ? flat.fontSize : 14;
    extra.fontSize = Math.round(baseFs * currentScale);
    // 줄 간격도 같은 배율로 — 고정 lineHeight 에 큰 글자가 들어가 위아래로 겹치는 것 방지
    if (typeof flat.lineHeight === 'number') {
      extra.lineHeight = Math.round(flat.lineHeight * currentScale);
    }
  }
  if (needFont) {
    extra.fontFamily = pickFamily(flat.fontWeight);
  }
  return {
    ...props,
    style: [props.style, extra],
    allowFontScaling: false,
  };
}

function patch(Comp: any) {
  if (!Comp || Comp.__tooktahScalePatched) return;
  const orig = Comp.render; // forwardRef 객체의 내부 렌더 함수 (props, ref) => element
  if (typeof orig === 'function') {
    Comp.render = function patchedRender(props: any, ref: any) {
      return orig.call(this, scaleProps(props), ref);
    };
    Comp.__tooktahScalePatched = true;
  }
}

patch(Text);
patch(TextInput);
