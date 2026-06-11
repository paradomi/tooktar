"""AI 경로 브리핑 — 템플릿 + Gemini Vision 도면 분석.

경로 데이터를 받아 교통약자 친화 안내 문구를 만든다.
지하철역 도면(KRIC imgPath) 있으면 Gemini Vision으로 자동 분석.
"""

import os
import requests


def analyze_subway_diagram(img_url, station_name="", target_direction=""):
    """KRIC 도면 이미지 → 휠체어 이용자용 자연어 안내 (Gemini Vision).

    Args:
        img_url: KRIC imgPath (http/https PNG)
        station_name: 역명 (프롬프트 컨텍스트)
        target_direction: 사용자가 가야 할 방면 (예: "매탄권선 방면")

    Returns:
        str | None: Gemini가 생성한 분석 텍스트. 실패 시 None.
    """
    api_key = os.getenv("Gemini", "")
    if not api_key or not img_url:
        return None

    # 이미지 다운로드 (https 우선, http fallback)
    img_bytes = None
    for u in (img_url.replace("http://", "https://", 1), img_url):
        try:
            r = requests.get(u, timeout=10)
            if r.status_code == 200 and r.content:
                img_bytes = r.content
                break
        except Exception:
            continue
    if not img_bytes:
        return None

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None

    prompt = (
        "당신은 휠체어 이용자를 위한 길안내 비서입니다. "
        f"이 지하철역({station_name}) 도면을 분석해서 다음을 알려주세요:\n\n"
        f"1. {target_direction or '목표 방면'}로 가는 가장 빠른 출입구\n"
        "2. 도면에 보이는 엘리베이터/리프트 위치 (있을 때만)\n"
        "3. 단차·계단 없이 갈 수 있는지\n"
        "4. 주의해야 할 지점\n\n"
        "조건:\n"
        "- 총 4~5문장 이내, 정중한 존댓말\n"
        "- 굵게 강조할 키워드는 **굵게** (마크다운)\n"
        "- 추측 X, 도면에 보이는 정보만\n"
        "- 도입부 인사말 없이 바로 본론으로"
    )

    try:
        client = genai.Client(api_key=api_key)
        img_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
    except Exception:
        return None

    # 모델 fallback: 2.5-flash → 2.0-flash → 1.5-flash
    for model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img_part],
                )
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as e:
                msg = str(e).lower()
                # 503/429 같은 일시적 오류면 다음 모델로
                if "503" in msg or "429" in msg or "unavailable" in msg or "overloaded" in msg:
                    break
                # 다른 에러면 다음 모델 시도
                break
    return None


def _gemini_text(contents):
    """Gemini 텍스트 생성 공통 헬퍼 — 모델 fallback (2.5 → 2.0 → 1.5 flash). 실패 시 None."""
    api_key = os.getenv("Gemini", "")
    if not api_key:
        return None
    try:
        from google import genai
    except Exception:
        return None
    try:
        client = genai.Client(api_key=api_key)
    except Exception:
        return None
    for model_name in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception:
            continue
    return None


def generate_journey_narrative(route, mode, origin_name, dest_name, transfers=None):
    """여정 예행연습 내러티브 + 환승 집중 브리핑 (Gemini 텍스트 생성).

    Args:
        route: 경로 dict (steps, total_minutes, transfers, total_walk)
        mode: "fast" / "wheel" / "walk_less"
        transfers: 환승 컨텍스트 목록
            [{"alight": 하차 설명, "board": 다음 승차 설명,
              "facility": KRIC 이동경로 요약, "arrival": 다음 차량 도착 정보, "walk": 환승 도보}]

    Returns:
        str | None: 마크다운 안내 텍스트. Gemini 실패 시 None (호출측 템플릿 유지).
    """
    steps = route.get("steps", []) or []
    if not steps:
        return None

    step_lines = []
    for s in steps:
        t = s.get("type")
        if t == "walk":
            step_lines.append(f"- 도보: {s.get('desc', '')}")
        elif t == "bus":
            step_lines.append(
                f"- 버스 {s.get('bus_no', '')}번: {s.get('start_name', '')} → "
                f"{s.get('end_name', '')} ({s.get('station_count', '?')}정거장)"
            )
        elif t == "subway":
            step_lines.append(
                f"- 지하철 {s.get('line_name', '')}: {s.get('start_name', '')} → "
                f"{s.get('end_name', '')} ({s.get('station_count', '?')}개 역)"
            )

    transfer_lines = []
    for i, tr in enumerate(transfers or [], 1):
        parts = [f"환승 {i}: {tr.get('alight', '')} 후 {tr.get('board', '')} 탑승"]
        if tr.get("walk"):
            parts.append(f"환승 도보: {tr['walk']}")
        if tr.get("facility"):
            parts.append(f"역내 이동경로(KRIC): {tr['facility']}")
        if tr.get("arrival"):
            parts.append(f"다음 차량: {tr['arrival']}")
        transfer_lines.append(" / ".join(parts))

    persona = (
        "휠체어 이용자" if mode == "wheel" else "고령자 등 교통약자"
    )
    prompt = (
        f"당신은 {persona}를 위한 따뜻하고 믿음직한 길안내 비서입니다.\n"
        f"아래 경로 데이터를 바탕으로 출발 전 브리핑을 작성하세요.\n\n"
        f"[여정] {origin_name} → {dest_name}, 총 {route.get('total_minutes', '?')}분, "
        f"환승 {route.get('transfers', 0)}회, 도보 총 {route.get('total_walk', 0)}m\n"
        f"[단계]\n" + "\n".join(step_lines) + "\n"
        + (("[환승 정보]\n" + "\n".join(transfer_lines) + "\n") if transfer_lines else "")
        + "\n출력 형식 (마크다운):\n"
        "1) 첫 단락: 여정 전체를 미리 그려주는 '예행연습' 3~4문장. "
        "이 경로에서 **가장 까다로운 구간 1곳**을 콕 짚어 이유와 대비 방법을 알려줄 것.\n"
        "2) 환승이 있으면 각 환승마다 새 단락으로 '🔄 환승 안내 — (장소)' 형식 제목 뒤에 "
        "2~3문장: 하차 후 이동 방법(엘리베이터 등 제공된 시설 정보 활용), 다음 차량 도착/저상 정보, 여유 시간 조언.\n\n"
        "규칙: 정중한 존댓말, 핵심 단어는 **굵게**, 제공된 정보만 사용(추측 금지), "
        "인사말 없이 바로 본론, 전체 10문장 이내."
    )
    return _gemini_text(prompt)


def _safe_int(v, default=0):
    try:
        return int(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _format_walk(meter):
    if meter <= 0:
        return ""
    if meter >= 1000:
        return f"{meter/1000:.1f}km"
    return f"{meter}m"


def generate_briefing(route, mode, origin_name, dest_name, diagram_insight=None):
    """경로 데이터 → 자연어 안내 문구 (markdown 형식).

    Args:
        route: 경로 dict (steps, total_minutes, transfers, total_walk, payment)
        mode: "fast" / "wheel" / "walk_less"
        origin_name: 출발지명
        dest_name: 도착지명

    Returns:
        str: 줄바꿈으로 구분된 안내 문장들 (HTML 미포함, 굵게는 **)
    """
    lines = []
    total = _safe_int(route.get("total_minutes"))
    transfers = _safe_int(route.get("transfers"))
    walk = _safe_int(route.get("total_walk"))
    payment = _safe_int(route.get("payment"))
    steps = route.get("steps", [])

    # ─── 1) 요약 ───
    summary = (
        f"📍 **{origin_name}**에서 **{dest_name}**까지 "
        f"총 **{total}분**"
    )
    if transfers > 0:
        summary += f", 환승 **{transfers}회**"
    summary += f", 요금 **{payment:,}원**입니다."
    lines.append(summary)

    # ─── 2) 단계별 핵심 안내 (실제 이동 순서대로) ───
    subway_steps = [s for s in steps if s.get("type") == "subway"]
    bus_steps = [s for s in steps if s.get("type") == "bus"]

    # steps를 순서대로 순회하며 지하철/버스를 그 자리에서 안내
    for s in steps:
        stype = s.get("type")
        if stype == "subway":
            line_name = s.get("line_name", "")
            start = s.get("start_name", "")
            end = s.get("end_name", "")
            st_cnt = _safe_int(s.get("station_count"))
            sec_time = _safe_int(s.get("section_time"))
            sentence = f"🚇 **{start}**역에서 **{line_name}**을 타고 **{end}**까지"
            if st_cnt > 0:
                sentence += f" **{st_cnt}개 역** 이동"
            if sec_time > 0:
                sentence += f" ({sec_time}분)"
            sentence += "합니다."
            lines.append(sentence)
        elif stype == "bus":
            bus_no = s.get("bus_no", "")
            start = s.get("start_name", "")
            end = s.get("end_name", "")
            st_cnt = _safe_int(s.get("station_count"))
            sec_time = _safe_int(s.get("section_time"))
            sentence = f"🚌 **{start}** 정류장에서 **{bus_no}번 버스**를 타고"
            if st_cnt > 0:
                sentence += f" **{st_cnt}정거장** 후"
            sentence += f" **{end}**에서 하차"
            if sec_time > 0:
                sentence += f" (약 {sec_time}분)"
            sentence += "합니다."
            lines.append(sentence)

    # ─── 3) 도보 안내 (길이에 따른 톤 조정) ───
    if walk >= 800:
        lines.append(
            f"⚠️ 이 경로는 도보가 총 **{_format_walk(walk)}**로 깁니다. "
            f"휠체어 배터리나 체력을 미리 확인해주세요."
        )
    elif walk >= 300:
        lines.append(f"🚶 도보 구간은 총 **{_format_walk(walk)}**입니다.")
    elif walk > 0:
        lines.append(f"🚶 도보는 **{_format_walk(walk)}**로 짧은 편입니다.")

    # ─── 4) 모드별 추가 안내 ───
    if mode == "wheel":
        lines.append(
            "♿ **휠체어 맞춤 경로**입니다. 계단을 제외한 도보로 안내하며, "
            "각 지하철역의 엘리베이터·출입구 정보는 아래 **교통약자 시설 정보** 탭에서 확인하세요."
        )
        if bus_steps:
            lines.append(
                "💡 버스 정류장에 도착하면 카드의 ⏱️ 도착 시간을 확인하고, "
                "**♿저상** 표시가 있는 차량을 선택해 탑승하세요."
            )
    elif mode == "walk_less":
        lines.append("🚶 **덜 걷는 경로**로 안내합니다. 환승이 적고 도보가 짧습니다.")

    # ─── 4.5) 도면 AI 분석 (있을 때) ───
    if diagram_insight:
        lines.append(f"🤖 **AI 도면 분석**: {diagram_insight}")

    # ─── 5) 마무리 ───
    if transfers >= 2:
        lines.append("🔄 환승이 여러 번 있으니 각 안내 카드를 꼼꼼히 확인해주세요.")

    if mode == "wheel":
        lines.append("✅ 안전한 이동 되세요.")
    else:
        lines.append("✅ 즐거운 이동 되세요.")

    return "\n\n".join(lines)
