"""경로 상세 화면 - ODsay mapObj 기반 실제 경로 + 카카오맵 + 교통약자 정보"""

import json
import streamlit as st
import streamlit.components.v1 as components
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from components.styles import apply_global_styles, FONT_SIZE_PRESETS
from components.header import render_header

NAVY = "#002F6C"
from services.odsay_api import load_lane
from services.tmap_api import pedestrian_route
from services.bus_arrival import get_arrivals as _get_bus_arrivals
from services.bus_arrival import has_low_floor_arriving as _has_lf_arriving
from services.bus_arrival import has_low_floor_on_route as _has_lf_route
from services.subway_arrival import get_next_trains as _get_next_trains
from services.rail_portal import find_station_codes as _find_station_codes
from services.kakao_local import find_nearest_exit as _find_nearest_exit
from services.kakao_local import find_station_exits as _find_station_exits
from services.ai_briefing import generate_briefing as _gen_briefing
from services.ai_briefing import analyze_subway_diagram as _analyze_diagram

st.set_page_config(page_title="경로 상세", page_icon="🗺️", layout="centered")

apply_global_styles()

st.markdown("""
<style>
/* 상세 페이지는 컨텐츠가 많지만 글로벌 max-width(1080px) 그대로 사용 */
.main .block-container { max-width: 1080px !important; }

[data-testid="stMain"] [data-testid="stTabs"] button[role="tab"] p {
    font-size: 1.6rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

level = st.session_state.get("font_size_level", "크게")
f = FONT_SIZE_PRESETS.get(level, FONT_SIZE_PRESETS["크게"])
fs_body = f["body"]
fs_small = max(fs_body - 4, 12)
fs_badge = max(fs_body - 6, 11)
fs_title = f["h3"]

import pandas as _pd

_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "station_codes.csv")
try:
    _stn_df = _pd.read_csv(_csv_path)
except Exception:
    _stn_df = None


def _stin_cd_of(line_cd, station_name):
    """노선코드 + 역명으로 STIN_CD 반환. 부분매칭 허용."""
    if _stn_df is None or _stn_df.empty:
        return None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    exact = sub[sub["STIN_NM"] == nm]
    if not exact.empty:
        return exact.iloc[0]["STIN_CD"]
    partial = sub[sub["STIN_NM"].str.startswith(nm, na=False)]
    if not partial.empty:
        return partial.iloc[0]["STIN_CD"]
    return None


def _stin_num(stin_cd):
    """STIN_CD에서 숫자만 추출해 int 반환 (비교용). 실패 시 None."""
    if not stin_cd:
        return None
    import re as _re
    m = _re.search(r"(\d+)", str(stin_cd))
    return int(m.group(1)) if m else None


def _line_terminals(line_cd):
    """노선의 양 끝 종점 역명 반환 (작은 STIN_CD 쪽, 큰 쪽)."""
    if _stn_df is None or _stn_df.empty:
        return None, None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    if sub.empty:
        return None, None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None, None
    pairs.sort(key=lambda p: p[0])
    return pairs[0][1], pairs[-1][1]  # (min_terminal, max_terminal)


def _line_cd_of_station(station_name):
    """역명으로 LN_CD 자동 추론 (첫 매칭). 환승역은 첫 노선만."""
    if _stn_df is None or _stn_df.empty:
        return None
    nm = (station_name or "").rstrip("역").strip()
    if not nm:
        return None
    rows = _stn_df[_stn_df["STIN_NM"] == nm]
    if rows.empty:
        rows = _stn_df[_stn_df["STIN_NM"].str.startswith(nm, na=False)]
    if rows.empty:
        return None
    return str(rows.iloc[0]["LN_CD"])


def _adjacent_station(line_cd, start_num, direction):
    """노선 내 start_num의 한 칸 옆 역명 반환 (direction: -1 또는 +1)."""
    if _stn_df is None or _stn_df.empty:
        return None
    sub = _stn_df[_stn_df["LN_CD"] == line_cd]
    if sub.empty:
        return None
    pairs = []
    for _, row in sub.iterrows():
        n = _stin_num(row["STIN_CD"])
        if n is not None:
            pairs.append((n, str(row["STIN_NM"])))
    if not pairs:
        return None
    pairs.sort(key=lambda p: p[0])
    nums = [p[0] for p in pairs]
    if start_num not in nums:
        return None
    idx = nums.index(start_num)
    nxt = idx + direction
    if 0 <= nxt < len(pairs):
        return pairs[nxt][1]
    return None


def _direction_label(start_name, end_name):
    """ODsay subway step의 (start_name, end_name)으로 (종점, 인접역) 방면 라벨 생성.
    실패 시 '{end_name} 방면' fallback."""
    fallback = f"{end_name} 방면"
    if not start_name or not end_name:
        return fallback
    ln_cd = _line_cd_of_station(start_name)
    if not ln_cd:
        return fallback
    start_num = _stin_num(_stin_cd_of(ln_cd, start_name))
    end_num = _stin_num(_stin_cd_of(ln_cd, end_name))
    if start_num is None or end_num is None or start_num == end_num:
        return fallback
    direction = -1 if end_num < start_num else +1
    t_low, t_high = _line_terminals(ln_cd)
    terminal = t_low if direction == -1 else t_high
    adj = _adjacent_station(ln_cd, start_num, direction)
    if terminal and adj and terminal != adj:
        return f"({terminal}, {adj}) 방면"
    if terminal:
        return f"{terminal} 방면"
    return fallback


def _render_station_panel(name, info, target_end_name=None, preferred_exit=None):
    """KRIC 데이터로 자체 교통약자 패널 렌더링 (출구/방면 선택형)"""
    import re
    NAVY_C = "#002F6C"
    full_nm = info.get("full_name", name)

    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:700;color:{NAVY_C};margin-bottom:8px;">'
        f'🚇 {full_nm}</div>',
        unsafe_allow_html=True,
    )

    movement = info.get("movement", [])
    if movement:
        # 이동 경로 그룹별로 정리 (mvPathMgNo로 구분)
        groups = {}
        for item in movement:
            mg = item.get("mvPathMgNo", 0)
            groups.setdefault(mg, []).append(item)

        # 출구별로 묶기 (stMovePath에서 "N번" 추출)
        exit_groups = {}  # {"3번 출입구": [(mg_no, items, ed_path), ...]}
        for mg_no, items in groups.items():
            items_sorted = sorted(items, key=lambda x: x.get("exitMvTpOrdr", 0))
            first = items_sorted[0]
            st_path = first.get("stMovePath", "")
            ed_path = first.get("edMovePath", "")

            # 출구 번호 추출 (예: "3번 출입구", "3번,4번 출입구 중간 엘리베이터")
            exit_nums = re.findall(r"(\d+)번", st_path)
            if exit_nums:
                if len(exit_nums) == 1:
                    exit_label = f"{exit_nums[0]}번 출입구"
                else:
                    exit_label = f"{','.join(exit_nums)}번 출입구"
            else:
                exit_label = st_path[:30] if st_path else f"경로 {mg_no}"

            exit_groups.setdefault(exit_label, []).append((mg_no, items_sorted, ed_path))

        # 출구 선택 UI
        exit_options = list(exit_groups.keys())
        exit_options.sort(key=lambda s: int(re.search(r"\d+", s).group()) if re.search(r"\d+", s) else 999)

        # 추론된 출구가 있으면 default 자동 선택 + ✓ (추천) 라벨
        # 매칭 실패해도 기본 선택(idx 0)에 ✓ 표시는 항상
        labeled_exit_options = list(exit_options)
        exit_default_idx = 0
        _matched_pref = False
        if preferred_exit:
            pref_num = re.search(r"\d+", preferred_exit)
            if pref_num:
                pref_n = pref_num.group()
                for i, opt in enumerate(exit_options):
                    nums_in_opt = re.findall(r"\d+", opt)
                    if pref_n in nums_in_opt:
                        labeled_exit_options[i] = f"✓ {opt} (추천)"
                        exit_default_idx = i
                        _matched_pref = True
                        break
        if not _matched_pref and labeled_exit_options:
            labeled_exit_options[exit_default_idx] = f"✓ {labeled_exit_options[exit_default_idx]}"

        selected_exit_labeled = st.selectbox(
            "이용할 출입구 선택",
            labeled_exit_options,
            index=exit_default_idx,
            key=f"exit_sel_{name}",
        )
        selected_exit = exit_options[labeled_exit_options.index(selected_exit_labeled)]

        # 해당 출구의 방면 옵션 (여러 방면 있으면)
        paths_for_exit = exit_groups[selected_exit]
        if len(paths_for_exit) > 1:
            # ── 방면 라벨 보강 + 자동 default 결정 ──
            ln_cd = info["codes"][1]
            start_stin_num = _stin_num(_stin_cd_of(ln_cd, name))
            target_stin_num = (
                _stin_num(_stin_cd_of(ln_cd, target_end_name))
                if target_end_name
                else None
            )

            target_dir = None  # +1 (증가), -1 (감소)
            if start_stin_num is not None and target_stin_num is not None:
                if target_stin_num < start_stin_num:
                    target_dir = -1
                elif target_stin_num > start_stin_num:
                    target_dir = +1

            terminal_low, terminal_high = _line_terminals(ln_cd)

            labeled_options = []
            default_idx = 0
            for i, (mg, items, ed_path) in enumerate(paths_for_exit):
                # ed_path 예: "매탄권선 방면" → head_word="매탄권선"
                head_word = ed_path.split(" ")[0] if ed_path else ""
                # 접미사 "행"이 붙은 경우 제거 (예: "왕십리행")
                head_clean = head_word.rstrip("행").strip()
                head_stin_num = _stin_num(_stin_cd_of(ln_cd, head_clean))

                opt_dir = None
                if start_stin_num is not None and head_stin_num is not None:
                    if head_stin_num < start_stin_num:
                        opt_dir = -1
                    elif head_stin_num > start_stin_num:
                        opt_dir = +1

                # 종점 결정
                if opt_dir == -1:
                    terminal = terminal_low
                elif opt_dir == +1:
                    terminal = terminal_high
                else:
                    terminal = None

                # 라벨 형식: "(종점, 인접역) 방면"
                if terminal and head_clean and terminal != head_clean:
                    base_label = f"({terminal}, {head_clean}) 방면"
                elif terminal:
                    base_label = f"{terminal} 방면"
                else:
                    base_label = ed_path

                # ✓ / 반대방향 표시
                if target_dir is not None and opt_dir == target_dir and target_end_name:
                    label = f"✓ {base_label}"
                    default_idx = i
                elif target_dir is not None and opt_dir is not None and opt_dir == -target_dir:
                    label = f"{base_label} (반대 방향)"
                else:
                    label = base_label
                labeled_options.append(label)

            # 매칭으로 ✓가 붙은 옵션이 없으면 기본 선택(default_idx)에 ✓ 추가
            if labeled_options and not any(opt.startswith("✓") for opt in labeled_options):
                labeled_options[default_idx] = f"✓ {labeled_options[default_idx]}"

            selected_label = st.selectbox(
                "방면 선택",
                labeled_options,
                index=default_idx,
                key=f"ed_sel_{name}_{selected_exit}",
            )
            selected_idx = labeled_options.index(selected_label)
            chosen = paths_for_exit[selected_idx]
        else:
            chosen = paths_for_exit[0]

        mg_no, items_sorted, ed_path = chosen
        first = items_sorted[0]
        st_path = first.get("stMovePath", "")

        # 선택된 경로 렌더링
        st.markdown(
            f'<div style="margin-top:14px;padding:10px 14px;'
            f'background:rgba(0,47,108,0.06);border-left:4px solid {NAVY_C};'
            f'border-radius:8px;">'
            f'<div style="font-weight:700;color:{NAVY_C};font-size:1rem;">'
            f'🛣️ {st_path} → {ed_path}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        img = first.get("imgPath", "")
        if img:
            img_https = img.replace("http://", "https://", 1)
            zoom_html = f'''
<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=yes" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#fff; }}
  #wrap {{ position:relative; width:100%; height:360px; overflow:hidden;
          border-radius:12px; border:1px solid #ddd; touch-action:none; }}
  #content {{ width:100%; height:100%; display:flex; align-items:center; justify-content:center; }}
  #content img {{ width:100%; max-width:600px; display:block; -webkit-user-drag:none; user-select:none; }}
  .hint {{ position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.55);
          color:white; font-size:11px; padding:4px 8px; border-radius:6px;
          pointer-events:none; font-family:sans-serif; z-index:2; }}
  .open-link {{ position:absolute; bottom:8px; right:8px; background:rgba(0,47,108,0.85);
                color:white; font-size:11px; padding:4px 9px; border-radius:6px;
                text-decoration:none; font-family:sans-serif; z-index:2; }}
  .open-link:hover {{ background:rgba(0,47,108,1); }}
</style>
</head><body>
<div id="wrap">
  <div id="content"><img src="{img_https}" alt="역내 도면" /></div>
  <div class="hint">🖱️ 휠 / 👆 핀치로 확대</div>
  <a class="open-link" href="{img_https}" target="_blank" rel="noopener">🔍 원본</a>
</div>
<script src="https://unpkg.com/panzoom@9.4.3/dist/panzoom.min.js"></script>
<script>
  window.addEventListener('load', function() {{
    var elem = document.getElementById('content');
    if (window.panzoom) {{
      panzoom(elem, {{
        minZoom: 1, maxZoom: 6,
        bounds: true, boundsPadding: 0.1,
        smoothScroll: false
      }});
    }}
  }});
</script>
</body></html>
'''
            components.html(zoom_html, height=380)
        for item in items_sorted:
            desc = item.get("mvContDtl", "")
            if desc:
                st.markdown(
                    f'<div style="padding:8px 14px;background:white;'
                    f'border:1px solid #e0e0e0;border-radius:8px;margin-top:6px;'
                    f'font-size:0.95rem;color:#333;">{desc}</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("이 역의 이동 경로 정보가 없습니다.")

    transfer = info.get("transfer", [])
    if transfer:
        with st.expander(f"🔄 환승 이동 정보 ({len(transfer)}건)"):
            for item in transfer:
                desc = item.get("mvContDtl") or item.get("dtLoc") or ""
                if desc:
                    st.markdown(f"- {desc}")

    lift = info.get("lift", [])
    if lift:
        with st.expander(f"♿ 휠체어 리프트 위치 ({len(lift)}건)"):
            for item in lift:
                exit_no = item.get("exitNo")
                loc = item.get("dtLoc") or item.get("liftLctnDtl") or item.get("mvContDtl") or ""
                # 층 정보: B1, 지하1층 → 지상1층 등
                fr = item.get("grndDvNmFr", "")
                fr_floor = item.get("runStinFlorFr", "")
                to = item.get("grndDvNmTo", "")
                to_floor = item.get("runStinFlorTo", "")
                floor_info = ""
                if fr and to and (fr_floor or to_floor):
                    floor_info = f" · {fr}{fr_floor}층 → {to}{to_floor}층"
                if exit_no:
                    label = f"**{exit_no}번 출입구**: {loc}{floor_info}"
                else:
                    label = f"{loc}{floor_info}" if loc else "위치 정보 없음"
                st.markdown(f"- {label}")


def _cached_station_exits(station_name):
    """역의 출구 좌표 dict (session_state 영구 캐시)."""
    ck = f"station_exits_{station_name}"
    if ck in st.session_state:
        return st.session_state[ck]
    exits = _find_station_exits(station_name)
    st.session_state[ck] = exits
    return exits


def _nearest_exit(station_name, lng, lat):
    if lng is None or lat is None:
        return None
    exits = _cached_station_exits(station_name)
    if not exits:
        return None
    best_no, best_d = None, float("inf")
    for no, (ex_lng, ex_lat) in exits.items():
        d = (ex_lng - lng) ** 2 + (ex_lat - lat) ** 2
        if d < best_d:
            best_d, best_no = d, no
    return best_no


def _infer_subway_exits(steps, origin_coord, dest_coord):
    """경로 step 흐름에서 각 지하철역의 진입/하차 출구 추론.
    Returns: {station_name: {"in": "7번", "out": "10번"}}
    """
    import re
    result = {}
    for i, s in enumerate(steps):
        if s.get("type") != "subway":
            continue
        st_name = s.get("start_name", "")
        end_name = s.get("end_name", "")
        if not st_name:
            continue
        # 진입 좌표: 사용자가 "출발한 곳" — 이전 walk의 start (또는 이전 transit의 end)
        in_lng = in_lat = None
        in_exit_from_name = None
        for j in range(i - 1, -1, -1):
            ps = steps[j]
            if ps.get("type") == "walk":
                # walk이면 start = 사용자가 출발한 곳
                if ps.get("start_x") and ps.get("start_y"):
                    in_lng, in_lat = ps["start_x"], ps["start_y"]
                    m = re.search(r"(\d+)번\s*출구", ps.get("start_name", "") or "")
                    if m:
                        in_exit_from_name = f"{m.group(1)}번"
                    break
            else:
                # transit이면 end = 직전 transit 종착
                if ps.get("end_x") and ps.get("end_y"):
                    in_lng, in_lat = ps["end_x"], ps["end_y"]
                    m = re.search(r"(\d+)번\s*출구", ps.get("end_name", "") or "")
                    if m:
                        in_exit_from_name = f"{m.group(1)}번"
                    break
        if in_lng is None and origin_coord:
            in_lng = origin_coord.get("lng")
            in_lat = origin_coord.get("lat")
        if in_exit_from_name:
            result.setdefault(st_name, {})["in"] = in_exit_from_name
        elif in_lng and in_lat:
            no = _nearest_exit(st_name, in_lng, in_lat)
            if no:
                result.setdefault(st_name, {})["in"] = f"{no}번"

        # 하차 좌표: 사용자가 "가야할 곳" — 다음 walk의 end (또는 다음 transit의 start)
        if end_name:
            out_lng = out_lat = None
            out_exit_from_name = None
            for j in range(i + 1, len(steps)):
                ns = steps[j]
                if ns.get("type") == "walk":
                    # walk이면 end = 사용자가 가야할 곳
                    if ns.get("end_x") and ns.get("end_y"):
                        out_lng, out_lat = ns["end_x"], ns["end_y"]
                        m = re.search(r"(\d+)번\s*출구", ns.get("end_name", "") or "")
                        if m:
                            out_exit_from_name = f"{m.group(1)}번"
                        break
                else:
                    # transit이면 start = 다음 transit 출발지
                    if ns.get("start_x") and ns.get("start_y"):
                        out_lng, out_lat = ns["start_x"], ns["start_y"]
                        m = re.search(r"(\d+)번\s*출구", ns.get("start_name", "") or "")
                        if m:
                            out_exit_from_name = f"{m.group(1)}번"
                        break
            if out_lng is None and dest_coord:
                out_lng = dest_coord.get("lng")
                out_lat = dest_coord.get("lat")
            if out_exit_from_name:
                result.setdefault(end_name, {})["out"] = out_exit_from_name
            elif out_lng and out_lat:
                no = _nearest_exit(end_name, out_lng, out_lat)
                if no:
                    result.setdefault(end_name, {})["out"] = f"{no}번"
    return result


def _resolve_exit_coord(station_name, target_lng, target_lat, preferred_exit_no=None):
    """역명 + 타겟 좌표 → 출구의 (lng, lat) 반환.

    우선순위:
      Tier 1: preferred_exit_no가 주어지고 출구 데이터에 존재 → 해당 출구 좌표 (정규식 추출 우선)
      Tier 2: 타겟 좌표에 가장 가까운 출구 좌표
    출구 데이터 없거나 target이 None이면 None.
    """
    if not station_name:
        return None
    exits = _cached_station_exits(station_name)
    if not exits:
        return None
    # Tier 1: 명시된 출구 번호 우선
    if preferred_exit_no is not None:
        try:
            n = int(preferred_exit_no)
            if n in exits:
                ex_lng, ex_lat = exits[n]
                return (float(ex_lng), float(ex_lat))
        except (TypeError, ValueError):
            pass
    # Tier 2: GPS 거리
    if target_lng is None or target_lat is None:
        return None
    best = None
    best_d = float("inf")
    for no, (ex_lng, ex_lat) in exits.items():
        try:
            d = (float(ex_lng) - float(target_lng)) ** 2 + (float(ex_lat) - float(target_lat)) ** 2
        except (TypeError, ValueError):
            continue
        if d < best_d:
            best_d = d
            best = (float(ex_lng), float(ex_lat))
    return best


render_header(back_target="pages/1_경로_탐색.py")

# 페이지 전환 플래그 처리
if st.session_state.get("_pending_nav"):
    target = st.session_state.pop("_pending_nav")
    st.switch_page(target)

KAKAO_JS_KEY = os.getenv("KAKAO_JS_KEY") or os.getenv("KAKAO_SDK_DOMAIN", "")

# ─── 선택된 경로 가져오기 ───
route_id = st.session_state.get("selected_route_id", 1)
odsay_routes = st.session_state.get("odsay_routes", [])
selected = next((r for r in odsay_routes if r["id"] == route_id), None)

if not selected:
    st.warning("경로 정보가 없습니다. 경로 탐색 페이지로 돌아가주세요.")
    st.stop()

steps = selected.get("steps", [])
map_obj = selected.get("map_obj", "")

_route_mode = st.session_state.get("route_mode", "fast")
_search_option = 4 if _route_mode == "wheel" else 0
_walk_color = "#7B1FA2" if _route_mode == "wheel" else "#FF8C00"

# ─── 1. ODsay loadLane으로 폴리라인 데이터 획득 ───
if _route_mode == "wheel":
    st.markdown(
        f'<div style="'
        f'background:rgba(0,47,108,0.08);'
        f'border-left:4px solid {NAVY};'
        f'border-radius:12px;'
        f'padding:14px 18px;'
        f'margin-bottom:16px;">'
        f'<div style="color:{NAVY};font-weight:700;font-size:1.05rem;margin-bottom:4px;">'
        f'♿ 휠체어 맞춤 경로</div>'
        f'<div style="color:#444;font-size:0.92rem;">'
        f'계단을 제외한 도보 경로로 안내합니다 (지도의 보라색 점선)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
st.markdown("### 🗺️ 경로 지도")

lane_data = None
if map_obj:
    cache_key = f"lane_{map_obj}"
    if cache_key in st.session_state:
        lane_data = st.session_state[cache_key]
    else:
        with st.spinner("🗺️ 실제 주행 경로를 불러오는 중..."):
            lane_data = load_lane(map_obj)
        if lane_data:
            st.session_state[cache_key] = lane_data

# ─── 2. 카카오맵에 폴리라인 렌더링 ───
lane_sections = []
if lane_data and "lane" in lane_data:
    for lane in lane_data["lane"]:
        lane_class = lane.get("class", 0)
        sections = lane.get("section", [])
        for section in sections:
            graph_pos = section.get("graphPos", [])
            coords = []
            if isinstance(graph_pos, list):
                for pt in graph_pos:
                    try:
                        coords.append({"lat": float(pt["y"]), "lng": float(pt["x"])})
                    except (KeyError, ValueError, TypeError):
                        pass
            elif isinstance(graph_pos, str) and graph_pos:
                for pt in graph_pos.split(" "):
                    parts = pt.split(",")
                    if len(parts) == 2:
                        try:
                            coords.append({"lat": float(parts[1]), "lng": float(parts[0])})
                        except ValueError:
                            pass
            if coords:
                if lane_class == 1:
                    color = "#2DB400"
                elif lane_class == 2:
                    color = "#1f77b4"
                else:
                    color = "#999999"
                lane_sections.append({"coords": coords, "color": color})

# 도보 구간 (Tmap 보행자 경로 API → 실패 시 직선 fallback)
origin_coord = st.session_state.get("origin_coord", {})
dest_coord = st.session_state.get("dest_coord", {})

walk_lines = []
for idx, step in enumerate(steps):
    if step["type"] != "walk":
        continue
    sx, sy = step.get("start_x"), step.get("start_y")
    ex, ey = step.get("end_x"), step.get("end_y")
    # 인접 step에서 좌표 보충
    if not (sx and sy):
        for j in range(idx - 1, -1, -1):
            ps = steps[j]
            if ps.get("end_x") and ps.get("end_y"):
                sx, sy = ps["end_x"], ps["end_y"]
                break
        if not (sx and sy) and origin_coord:
            sx, sy = origin_coord.get("lng"), origin_coord.get("lat")
    if not (ex and ey):
        for j in range(idx + 1, len(steps)):
            ns = steps[j]
            if ns.get("start_x") and ns.get("start_y"):
                ex, ey = ns["start_x"], ns["start_y"]
                break
        if not (ex and ey) and dest_coord:
            ex, ey = dest_coord.get("lng"), dest_coord.get("lat")
    if not (sx and sy and ex and ey):
        continue
    # 지하철 출구 기반 끝점 보정
    prev_step = steps[idx - 1] if idx > 0 else None
    next_step = steps[idx + 1] if idx + 1 < len(steps) else None

    import re as _re_exit
    # 다음 step이 subway → walk 끝점을 출구 좌표로 보정
    #   Tier1: walk의 end_name에서 "N번 출구" 추출 → 그 출구
    #   Tier2: walk 시작점에 가장 가까운 출구
    if next_step and next_step.get("type") == "subway":
        station_nm = next_step.get("start_name", "")
        _m = _re_exit.search(r"(\d+)번\s*출구", step.get("end_name", "") or "")
        _pref = _m.group(1) if _m else None
        new_end = _resolve_exit_coord(station_nm, sx, sy, preferred_exit_no=_pref)
        if new_end:
            ex, ey = new_end

    # 이전 step이 subway → walk 시작점을 출구 좌표로 보정
    if prev_step and prev_step.get("type") == "subway":
        station_nm = prev_step.get("end_name", "")
        _m = _re_exit.search(r"(\d+)번\s*출구", step.get("start_name", "") or "")
        _pref = _m.group(1) if _m else None
        new_start = _resolve_exit_coord(station_nm, ex, ey, preferred_exit_no=_pref)
        if new_start:
            sx, sy = new_start

    cache_key = f"tmap_walk_{sx}_{sy}_{ex}_{ey}_opt{_search_option}"
    tmap_coords = st.session_state.get(cache_key)
    if not tmap_coords:
        tmap_coords = pedestrian_route(
            sx, sy, ex, ey,
            start_name=step.get("start_name", "출발"),
            end_name=step.get("end_name", "도착"),
            search_option=_search_option,
        )
        if tmap_coords:
            st.session_state[cache_key] = tmap_coords
    if tmap_coords:
        coords = tmap_coords
    else:
        coords = [
            {"lat": float(sy), "lng": float(sx)},
            {"lat": float(ey), "lng": float(ex)},
        ]
    walk_lines.append({"coords": coords, "color": _walk_color})

all_coords = []
for sec in lane_sections:
    all_coords.extend(sec["coords"])
for wl in walk_lines:
    all_coords.extend(wl["coords"])
if origin_coord:
    all_coords.append({"lat": origin_coord.get("lat", 0), "lng": origin_coord.get("lng", 0)})
if dest_coord:
    all_coords.append({"lat": dest_coord.get("lat", 0), "lng": dest_coord.get("lng", 0)})

if not all_coords:
    all_coords = [{"lat": 37.27, "lng": 127.03}]

center_lat = sum(c["lat"] for c in all_coords) / len(all_coords)
center_lng = sum(c["lng"] for c in all_coords) / len(all_coords)

sections_json = json.dumps(lane_sections, ensure_ascii=False)
walk_json = json.dumps(walk_lines, ensure_ascii=False)

origin_name = origin_coord.get("name", "출발") if origin_coord else "출발"
dest_name = dest_coord.get("name", "도착") if dest_coord else "도착"
origin_lat = origin_coord.get("lat", center_lat)
origin_lng = origin_coord.get("lng", center_lng)
dest_lat = dest_coord.get("lat", center_lat)
dest_lng = dest_coord.get("lng", center_lng)

kakao_map_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&autoload=false"></script>
<style>
  * {{ margin: 0; padding: 0; }}
  #map {{ width: 100%; height: 450px; border-radius: 16px; }}
</style>
</head><body>
<div id="map"></div>
<script>
kakao.maps.load(function() {{
  var container = document.getElementById('map');
  var map = new kakao.maps.Map(container, {{
    center: new kakao.maps.LatLng({center_lat}, {center_lng}),
    level: 5,
    mapTypeId: kakao.maps.MapTypeId.HYBRID
  }});

  // 일반/위성 토글 컨트롤 (우측 상단)
  var mapTypeControl = new kakao.maps.MapTypeControl();
  map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
  // 줌 컨트롤
  var zoomControl = new kakao.maps.ZoomControl();
  map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

  var bounds = new kakao.maps.LatLngBounds();

  // 위성 배경 가시성 ↑ : 흰색 외곽 + 컬러 안쪽 두 겹 폴리라인
  var sections = {sections_json};
  sections.forEach(function(sec) {{
    var path = sec.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    // 외곽선 (흰색, 두꺼움)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 11, strokeColor: '#FFFFFF',
      strokeOpacity: 0.95, strokeStyle: 'solid'
    }});
    // 안쪽 (컬러)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 7, strokeColor: sec.color,
      strokeOpacity: 1.0, strokeStyle: 'solid'
    }});
  }});

  var walks = {walk_json};
  walks.forEach(function(w) {{
    var path = w.coords.map(function(c) {{
      var ll = new kakao.maps.LatLng(c.lat, c.lng);
      bounds.extend(ll);
      return ll;
    }});
    // 외곽선 (흰색, 점선)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 8, strokeColor: '#FFFFFF',
      strokeOpacity: 0.9, strokeStyle: 'shortdashdot'
    }});
    // 안쪽 (컬러)
    new kakao.maps.Polyline({{
      map: map, path: path,
      strokeWeight: 5, strokeColor: w.color,
      strokeOpacity: 1.0, strokeStyle: 'shortdashdot'
    }});
  }});

  var startPos = new kakao.maps.LatLng({origin_lat}, {origin_lng});
  bounds.extend(startPos);
  new kakao.maps.InfoWindow({{
    content: '<div style="padding:4px 8px;font-size:12px;font-weight:bold;color:#1565c0;">\\ud83d\\udea9 {origin_name}</div>'
  }}).open(map, new kakao.maps.Marker({{ map: map, position: startPos }}));

  var endPos = new kakao.maps.LatLng({dest_lat}, {dest_lng});
  bounds.extend(endPos);
  new kakao.maps.InfoWindow({{
    content: '<div style="padding:4px 8px;font-size:12px;font-weight:bold;color:#c62828;">\\ud83d\\udccd {dest_name}</div>'
  }}).open(map, new kakao.maps.Marker({{ map: map, position: endPos }}));

  map.setBounds(bounds, 80);
}});
</script>
</body></html>"""

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(static_dir, exist_ok=True)
map_file = os.path.join(static_dir, "map.html")
with open(map_file, "w", encoding="utf-8") as f:
    f.write(kakao_map_html)

components.iframe("app/static/map.html", height=470, scrolling=False)

_walk_legend = (
    '<span>🟪 <b>도보 (계단 제외)</b></span>'
    if _route_mode == "wheel"
    else '<span>🟧 <b>도보</b></span>'
)
st.markdown(f"""
<div style="display:flex;gap:16px;justify-content:center;font-size:13px;margin-top:-8px;margin-bottom:12px;">
    <span>🟦 <b>지하철</b></span>
    <span>🟩 <b>버스</b></span>
    {_walk_legend}
</div>
""", unsafe_allow_html=True)

# ─── 3. 경로 요약 ───
st.markdown(f"### 📋 {selected['total_minutes']}분 · {selected['summary']}")
st.caption(f"💰 요금 {selected.get('payment', 0):,}원 · 🚶 도보 {selected.get('total_walk', 0)}m")

# ─── 4. 경로 단계별 정보 ───
for _i, step in enumerate(steps):
    icon = {"walk": "🚶", "bus": "🚌", "transfer": "🔄", "subway": "🚇"}.get(step["type"], "•")
    stype = step["type"]

    # 환승 도보 판별: walk 인데 앞뒤가 모두 transit(bus/subway)
    is_transfer_walk = False
    if stype == "walk":
        prev_is_transit = _i > 0 and steps[_i - 1].get("type") in ("bus", "subway")
        next_is_transit = _i + 1 < len(steps) and steps[_i + 1].get("type") in ("bus", "subway")
        is_transfer_walk = prev_is_transit and next_is_transit

    if stype == "bus":
        border_color = "#1f77b4"
    elif stype == "subway":
        border_color = "#2DB400"
    elif stype == "walk":
        border_color = "#7B1FA2" if is_transfer_walk else "#FF8C00"
    else:
        border_color = "#999"

    if stype in ("bus", "subway"):
        # 방면 강조 카드
        if stype == "subway":
            line = step.get("line_name", "")
            head = f"{icon} {line}"
        else:  # bus
            bus_no = step.get("bus_no", "")
            head = f"{icon} {bus_no}번 버스"
            # ODsay bus_type은 저상 정보 아님 — GBIS 실시간 lowPlate로만 판단

        start_nm = step.get("start_name", "")
        end_nm = step.get("end_name", "")
        station_count = step.get("station_count", 0)
        section_time = step.get("section_time", 0)
        meta_unit = "역" if stype == "subway" else "정거장"

        # 지하철: (종점, 인접역) 방면 자동 추론, 버스는 단순 도착역 방면
        if stype == "subway":
            direction_label = _direction_label(start_nm, end_nm)
        else:
            direction_label = f"{end_nm} 방면"
        # 방면 앞에 출발 정류소 이름 prefix (| 구분자)
        if start_nm:
            direction_label = f"{start_nm} | {direction_label}"

        # 실시간 도착정보 (버스=GBIS, 지하철=한국철도공사)
        arrival_html = ""
        if stype == "subway":
            # 지하철 도착 시각 (캐시, 방향별 분리)
            sub_ck = f"sub_arr_v2_{start_nm}_{end_nm}"
            if sub_ck in st.session_state:
                sub_info = st.session_state[sub_ck]
            else:
                codes = _find_station_codes(start_nm)
                end_codes = _find_station_codes(end_nm) if end_nm else None
                to_cd = end_codes[2] if end_codes else None
                if codes:
                    rail_op, ln_cd_v, stin_cd_v, _ = codes
                    sub_info = _get_next_trains(
                        rail_op, ln_cd_v, stin_cd_v, limit=2, to_stin_cd=to_cd
                    )
                else:
                    sub_info = {"trains": [], "last_dpt": None, "status": "no_data"}
                st.session_state[sub_ck] = sub_info
            sub_status = sub_info.get("status", "no_data") if isinstance(sub_info, dict) else "no_data"
            sub_trains = sub_info.get("trains", []) if isinstance(sub_info, dict) else []
            sub_last_dpt = sub_info.get("last_dpt") if isinstance(sub_info, dict) else None
            if sub_status == "ok" and sub_trains:
                badges = []
                for t in sub_trains:
                    m = t.get("minutes_until")
                    dest = t.get("destination", "")
                    dest_str = f" ({dest}행)" if dest else ""
                    badges.append(f"<b>{m}분 후</b>{dest_str}")
                if sub_last_dpt:
                    badges.append(f"<span style='color:#666;font-weight:500;'>막차 {sub_last_dpt}</span>")
                arrival_html = (
                    f'<div style="background:rgba(0,47,108,0.08);border-radius:10px;'
                    f'padding:10px 14px;margin:8px 0;font-size:1.4rem;color:{NAVY};font-weight:600;'
                    f'font-family:\'Gowun Batang\',\'Noto Serif KR\',serif;">'
                    f'⏱️ {" · ".join(badges)}</div>'
                )
            elif sub_status == "after_last":
                last_str = f" (막차 {sub_last_dpt})" if sub_last_dpt else ""
                arrival_html = (
                    f'<div style="background:rgba(120,120,120,0.12);border-radius:10px;'
                    f'padding:10px 14px;margin:8px 0;font-size:1.4rem;color:#666;font-weight:600;'
                    f'font-family:\'Gowun Batang\',\'Noto Serif KR\',serif;">'
                    f'⏱️ 오늘 운행 종료{last_str}</div>'
                )
            elif sub_status == "no_data":
                arrival_html = (
                    f'<div style="background:rgba(120,120,120,0.08);border-radius:10px;'
                    f'padding:10px 14px;margin:8px 0;font-size:1.2rem;color:#888;font-weight:500;'
                    f'font-family:\'Gowun Batang\',\'Noto Serif KR\',serif;">'
                    f'⏱️ 도착 정보 없음</div>'
                )
        if stype == "bus":
            bus_no = step.get("bus_no", "")
            sx, sy = step.get("start_x"), step.get("start_y")
            station_id = step.get("start_id")
            ods_city = step.get("city_code")
            start_nm_for_bus = step.get("start_name", "")
            cache_k = f"bus_arr_v2_{station_id}_{bus_no}_{sx}_{sy}"
            if cache_k in st.session_state:
                arrivals = st.session_state[cache_k]
            else:
                arrivals = _get_bus_arrivals(
                    station_id=station_id, lng=sx, lat=sy,
                    city_code_hint=ods_city, station_name=start_nm_for_bus,
                )
                st.session_state[cache_k] = arrivals
            matched = [a for a in (arrivals or []) if a.get("route_name") == bus_no]
            if matched:
                preds = matched[0].get("predictions", [])[:2]
                if preds:
                    badges = []
                    has_low_floor = False
                    for p in preds:
                        m = p.get("minutes")
                        is_low = p.get("low_floor")
                        low_tag = f' <span style="background:{NAVY};color:white;font-size:1.05rem;font-weight:700;padding:3px 10px;border-radius:10px;">♿저상</span>' if is_low else ""
                        if is_low:
                            has_low_floor = True
                        stops = f" ({p['stops_left']}정류장 전)" if p.get("stops_left") else ""
                        badges.append(f"<b>{m}분 후</b>{low_tag}{stops}")
                    # 도착예정 첫 두 대에 저상 없으면 노선 단위 위치 검증
                    lf_on_route = has_low_floor
                    if not lf_on_route and bus_no:
                        loc_ck = f"lf_loc_v3_{station_id or 'no'}_{bus_no}"
                        if loc_ck in st.session_state:
                            lf_on_route = st.session_state[loc_ck]
                        else:
                            if station_id:
                                lf_on_route = _has_lf_arriving(station_id, bus_no, max_stops_ahead=15)
                            else:
                                lf_on_route = _has_lf_route(bus_no)
                            st.session_state[loc_ck] = lf_on_route
                    if lf_on_route:
                        label_text = "♿ 저상 도착" if has_low_floor else "♿ 노선에 저상 운행"
                        head += (
                            f' <span style="display:inline-block;background:{NAVY};color:white;'
                            f'font-size:1.1rem;font-weight:700;padding:4px 12px;border-radius:12px;'
                            f'margin-left:8px;vertical-align:middle;">{label_text}</span>'
                        )
                    arrival_html = (
                        f'<div style="background:rgba(0,47,108,0.08);border-radius:10px;'
                        f'padding:10px 14px;margin:8px 0;font-size:1.4rem;color:{NAVY};font-weight:600;'
                        f'font-family:\'Gowun Batang\',\'Noto Serif KR\',serif;">'
                        f'⏱️ {" · ".join(badges)}</div>'
                    )

        _gf = "'Gowun Batang', 'Noto Serif KR', serif"
        st.markdown(
            f'<div style="padding:14px 18px;background:#f8f9fa;'
            f'border-left:5px solid {border_color};margin-bottom:6px;'
            f'border-radius:10px;font-size:{fs_body}px;color:#333;'
            f'font-family:{_gf};">'
            f'<div style="font-weight:700;margin-bottom:4px;font-family:{_gf};">{head}</div>'
            f'<div style="font-size:{fs_body + 2}px;color:{NAVY};font-weight:700;'
            f'margin:6px 0;font-family:{_gf};">↗ {direction_label}</div>'
            f'{arrival_html}'
            f'<div style="display:flex;align-items:center;gap:10px;margin:10px 0 4px 0;'
            f'padding:8px 12px;background:rgba(0,47,108,0.05);border-radius:8px;'
            f'font-family:{_gf};font-size:{fs_body}px;flex-wrap:wrap;">'
            f'<span style="color:#666;font-size:{max(fs_body - 2, 12)}px;">승차</span>'
            f'<b style="color:{NAVY};">{start_nm}</b>'
            f'<span style="color:#999;">→</span>'
            f'<span style="color:#666;font-size:{max(fs_body - 2, 12)}px;">하차</span>'
            f'<b style="color:{NAVY};">{end_nm}</b>'
            f'</div>'
            f'<div style="font-size:{max(fs_body - 2, 13)}px;color:#666;'
            f'font-family:{_gf};">'
            f'{station_count}{meta_unit} · {section_time}분 이동</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _gf = "'Gowun Batang', 'Noto Serif KR', serif"
        if is_transfer_walk:
            _sec = step.get("section_time", 0)
            _dist_m = 0
            try:
                # step["desc"]에는 "(245m)" 형태로 거리 들어있음 — 정규식으로 추출
                import re as _re
                _dm = _re.search(r"\((\d+)m\)", step.get("desc", ""))
                if _dm:
                    _dist_m = int(_dm.group(1))
            except Exception:
                pass
            _dist_str = f" ({_dist_m}m)" if _dist_m else ""
            _label = f"🔄 환승 도보 <b>{_sec}분</b>{_dist_str}"
            _bg = "#f3e5f5"  # 연보라
            _fg = "#4A148C"
        else:
            _label = f"{icon} {step['desc']}"
            _bg = "#f8f9fa"
            _fg = "#333"
        st.markdown(
            f'<div style="padding:12px 16px;background:{_bg};'
            f'border-left:5px solid {border_color};margin-bottom:4px;'
            f'border-radius:8px;font-size:{fs_body}px;color:{_fg};'
            f'font-family:{_gf};font-weight:{"600" if is_transfer_walk else "400"};">'
            f'{_label}'
            f'</div>',
            unsafe_allow_html=True,
        )

st.write("---")

# 지하철역 진입/하차 출구 자동 추론 (도보 좌표 + 카카오 출구 좌표 매칭)
_subway_exits = _infer_subway_exits(steps, origin_coord, dest_coord)

# ─── 5. 교통약자 시설 정보 (카카오맵 지하철역 임베드) ───
st.markdown("### ♿ 교통약자 시설 정보")

subway_steps = [s for s in steps if s["type"] == "subway"]
station_names = []
_seen = set()
for s in subway_steps:
    for nm in (s.get("start_name", ""), s.get("end_name", "")):
        if nm and nm not in _seen:
            station_names.append(nm)
            _seen.add(nm)

if station_names:
    # KRIC 역코드 매핑 (캐시)
    from services.rail_portal import (
        find_station_codes, get_station_movement,
        get_elevator_movement, get_transfer_movement, get_wheelchair_lift,
    )

    station_data = {}  # {역명: {codes, movement, elevator, transfer, lift, full_name}}
    for nm in station_names:
        cache_key = f"kric_{nm}"
        if cache_key in st.session_state:
            station_data[nm] = st.session_state[cache_key]
            continue
        codes = find_station_codes(nm)
        if not codes:
            continue
        rail_op, ln, stin, full_nm = codes
        info = {
            "codes": (rail_op, ln, stin),
            "full_name": full_nm,
            "movement": get_station_movement(rail_op, ln, stin),
            "elevator": get_elevator_movement(rail_op, ln, stin),
            "transfer": get_transfer_movement(rail_op, ln, stin),
            "lift": get_wheelchair_lift(rail_op, ln, stin),
        }
        station_data[nm] = info
        st.session_state[cache_key] = info

    if station_data:
        names = list(station_data.keys())
        tabs = st.tabs([f"🚇 {n}" for n in names])
        for tab, nm in zip(tabs, names):
            # subway step 중 시작역이 nm인 것 찾기 → target_end_name 전달
            target_end = None
            for s in subway_steps:
                s_start = s.get("start_name", "")
                if s_start == nm or s_start.startswith(nm) or nm.startswith(s_start):
                    target_end = s.get("end_name", "")
                    break
            with tab:
                info = station_data[nm]
                # 추론된 출구 — 진입 정류장은 'in', 하차 정류장은 'out'
                _ex_info = _subway_exits.get(nm, {})
                _pref_exit = _ex_info.get("in") or _ex_info.get("out")
                _render_station_panel(
                    nm, info,
                    target_end_name=target_end,
                    preferred_exit=_pref_exit,
                )
    else:
        st.info("이 경로의 지하철역 교통약자 정보를 불러올 수 없습니다.")
else:
    st.info("이 경로에는 지하철 구간이 없습니다.")
    
st.write("---")

# ─── 6. AI 요약 브리핑 (Gemini Vision 도면 분석 포함) ───
st.markdown("### 🤖 AI 경로 브리핑")

# 휠체어 모드일 때만 첫 지하철역 도면 분석 (Gemini 호출 비용 절감)
_diagram_text = None
if _route_mode == "wheel":
    _first_subway = next(
        (s for s in steps if s.get("type") == "subway" and s.get("start_name")),
        None,
    )
    if _first_subway:
        _sub_start = _first_subway.get("start_name", "")
        _sub_end = _first_subway.get("end_name", "")
        _sub_dir = _direction_label(_sub_start, _sub_end)
        # station_data에서 도면 imgPath 추출
        _sd = (station_data or {}).get(_sub_start)
        if _sd:
            _mv = _sd.get("movement", [])
            _img = next(
                (it.get("imgPath") for it in _mv if it.get("imgPath")),
                None,
            )
            if _img:
                _ai_ck = f"diagram_ai_{_sub_start}_{_sub_dir}"
                if _ai_ck in st.session_state:
                    _diagram_text = st.session_state[_ai_ck]
                else:
                    with st.spinner("🤖 도면을 AI가 분석 중..."):
                        _diagram_text = _analyze_diagram(_img, _sub_start, _sub_dir)
                    st.session_state[_ai_ck] = _diagram_text

# 추론된 출구를 brifing에 합쳐 전달 (diagram_insight 앞에 prepend)
_exit_lines = []
for st_name, ex in _subway_exits.items():
    parts = []
    if ex.get("in"):
        parts.append(f"**{ex['in']} 출입구**로 진입")
    if ex.get("out"):
        parts.append(f"**{ex['out']} 출입구**로 하차")
    if parts:
        _exit_lines.append(f"🚇 **{st_name}**: " + " / ".join(parts))
_exit_block = "\n".join(_exit_lines) if _exit_lines else None
if _exit_block:
    _diagram_text = (_exit_block + ("\n\n" + _diagram_text if _diagram_text else ""))

_briefing_text = _gen_briefing(
    selected,
    _route_mode,
    origin_name,
    dest_name,
    diagram_insight=_diagram_text,
)
# **굵게** → <strong>, 줄바꿈 → <br>
import re as _re
_briefing_html = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _briefing_text)
_briefing_html = _briefing_html.replace("\n\n", "<br><br>").replace("\n", "<br>")
st.markdown(
    f'<div style="background:linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);'
    f'border-left:4px solid {NAVY};border-radius:12px;padding:18px;'
    f'font-size:{fs_body}px;line-height:1.7;color:#222;'
    f'font-family:\'Gowun Batang\',\'Noto Serif KR\',serif;">'
    f'{_briefing_html}</div>',
    unsafe_allow_html=True,
)

st.write("")

# ─── 액션 버튼 ───
_act1, _act2 = st.columns(2)
with _act1:
    if st.button("🔊 음성 안내", key="action_voice", use_container_width=True):
        st.toast("음성 안내를 시작합니다")
with _act2:
    if st.button("📤 보호자 공유", key="action_share", use_container_width=True, type="primary"):
        st.toast("보호자에게 경로를 공유했습니다")
