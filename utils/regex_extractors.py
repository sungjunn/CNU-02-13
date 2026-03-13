"""정규식 기반 추출 함수 모음.

한국어/영어 특허 문서 패턴 모두 지원.
확정적(deterministic) 데이터 추출에 사용한다."""

import re


def extract_rejection_articles(text: str) -> list[str]:
    """거절 법조항 추출.

    지원 패턴:
        한국: "제29조 제1항", "제29조 제2항", "제36조", "제42조제3항제1호" 등
        미국: "35 U.S.C. 102", "35 U.S.C. 103" 등

    Returns:
        중복 제거된 법조항 리스트 (예: ["제29조 제2항", "제42조 제3항"])
    """
    results = set()

    # 한국 특허법 패턴: "제29조 제1항", "제29조제2항", "제42조제3항제1호" 등
    kr_pattern = re.compile(r"제(\d+)조\s*(?:제(\d+)항)?(?:\s*제(\d+)호)?")
    for m in kr_pattern.finditer(text):
        article = f"제{m.group(1)}조"
        if m.group(2):
            article += f" 제{m.group(2)}항"
        if m.group(3):
            article += f" 제{m.group(3)}호"
        results.add(article)

    # 미국 특허법 패턴: "35 U.S.C. 102", "35 U.S.C. § 103" 등
    us_pattern = re.compile(r"35\s*U\.?S\.?C\.?\s*§?\s*(\d+)")
    for m in us_pattern.finditer(text):
        results.add(f"35 U.S.C. {m.group(1)}")

    return sorted(results)


def extract_patent_numbers(text: str) -> list[str]:
    """특허번호 추출.

    지원 패턴:
        한국: "KR10-1234567", "KR 10-2020-0123456", "특허 제10-1234567호"
        미국: "US 11,234,567", "US2020/0123456", "US 7,123,456 B2"
        일본: "JP2007-141071", "JP특허 제1234567호"
        유럽: "EP 1 234 567"

    Returns:
        중복 제거된 특허번호 리스트
    """
    results = set()

    # 한국 특허번호: KR10-1234567, KR 10-2020-0123456
    kr_pattern = re.compile(
        r"(?:KR\s*)?10-(?:\d{4}-)?(\d{7})"
    )
    for m in kr_pattern.finditer(text):
        full = m.group(0).strip()
        if not full.startswith("KR"):
            full = "KR" + full
        results.add(full)

    # "특허 제10-XXXXXXX호" 패턴
    kr_title_pattern = re.compile(r"특허\s*제?(10-\d{7})호?")
    for m in kr_title_pattern.finditer(text):
        results.add(f"KR{m.group(1)}")

    # 미국 특허번호: US 11,234,567 또는 US2020/0123456
    us_pattern = re.compile(r"US\s*(?:\d{1,2},)?\d{3},\d{3}(?:\s*[AB]\d)?")
    for m in us_pattern.finditer(text):
        results.add(m.group(0).strip())

    us_pub_pattern = re.compile(r"US\s*\d{4}/\d{7}")
    for m in us_pub_pattern.finditer(text):
        results.add(m.group(0).strip())

    # 일본 특허번호: JP2007-141071
    jp_pattern = re.compile(r"JP\s*\d{4}-\d{4,6}")
    for m in jp_pattern.finditer(text):
        results.add(m.group(0).strip())

    # 유럽 특허번호: EP 1 234 567
    ep_pattern = re.compile(r"EP\s*\d[\d\s]{5,}")
    for m in ep_pattern.finditer(text):
        # 공백 정리
        num = re.sub(r"\s+", " ", m.group(0).strip())
        results.add(num)

    return sorted(results)


def extract_claim_numbers(text: str) -> list[int]:
    """거절 대상 청구항 번호 추출.

    지원 패턴:
        한국: "제1항", "제3항, 제5항", "청구항 1, 3, 5"
        영문: "claims 1, 3, 5", "claim 1"

    Returns:
        정렬된 청구항 번호 리스트 (중복 제거)
    """
    results = set()

    # "제N항" 패턴
    kr_pattern = re.compile(r"제\s*(\d+)\s*항")
    for m in kr_pattern.finditer(text):
        results.add(int(m.group(1)))

    # "청구항 1, 3, 5" 또는 "청구항 1 내지 5"
    kr_range_pattern = re.compile(r"청구항\s*([\d,\s~내지\-]+)")
    for m in kr_range_pattern.finditer(text):
        chunk = m.group(1)
        # 개별 번호
        for n in re.findall(r"\d+", chunk):
            results.add(int(n))
        # "N 내지 M" 또는 "N~M" 범위
        range_m = re.search(r"(\d+)\s*(?:내지|~|-)\s*(\d+)", chunk)
        if range_m:
            start, end = int(range_m.group(1)), int(range_m.group(2))
            results.update(range(start, end + 1))

    # 영문: "claims 1, 3, 5" 또는 "claim 1"
    en_pattern = re.compile(r"claims?\s+([\d,\s\-and]+)", re.IGNORECASE)
    for m in en_pattern.finditer(text):
        for n in re.findall(r"\d+", m.group(1)):
            results.add(int(n))

    return sorted(results)


def classify_rejection_type(articles: list[str]) -> str:
    """법조항으로 거절 유형 판별.

    규칙:
        제29조 제1항 / 35 U.S.C. 102 → "신규성"
        제29조 제2항 / 35 U.S.C. 103 → "진보성"
        그 외 → "기타"

    여러 법조항이 있으면 가장 심각한 것 기준 (진보성 > 신규성).
    """
    has_novelty = False
    has_inventive = False

    for art in articles:
        if "제29조" in art and "제1항" in art:
            has_novelty = True
        elif "제29조" in art and "제2항" in art:
            has_inventive = True
        elif "102" in art:
            has_novelty = True
        elif "103" in art:
            has_inventive = True

    if has_inventive:
        return "진보성"
    elif has_novelty:
        return "신규성"
    else:
        return "기타"


def split_claims(text: str) -> list[dict]:
    """청구항 텍스트를 개별 청구항으로 분리.

    지원 패턴:
        "【청구항 1】" 또는 "[청구항 1]" 또는 "제1항" 또는 "1." 시작

    Returns:
        [{"number": 1, "text": "...", "is_dependent": False, "depends_on": None}, ...]
    """
    claims = []

    # 패턴 1: 【청구항 N】 또는 [청구항 N]
    bracket_pattern = re.compile(r"[【\[]\s*청구항\s*(\d+)\s*[】\]]")
    # 패턴 2: 제N항 또는 N. 으로 시작
    number_pattern = re.compile(r"(?:^|\n)\s*(?:제\s*(\d+)\s*항|(\d+)\s*\.)\s*")

    # 먼저 bracket 패턴 시도
    splits = list(bracket_pattern.finditer(text))
    if splits:
        for i, m in enumerate(splits):
            num = int(m.group(1))
            start = m.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            claim_text = text[start:end].strip()

            claim_type, depends_on = classify_claim_type(claim_text)
            claims.append({
                "number": num,
                "text": claim_text,
                "is_dependent": claim_type == "종속항",
                "depends_on": depends_on,
            })
        return claims

    # bracket 패턴이 없으면 number 패턴 시도
    splits = list(number_pattern.finditer(text))
    if splits:
        for i, m in enumerate(splits):
            num = int(m.group(1) or m.group(2))
            start = m.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            claim_text = text[start:end].strip()

            claim_type, depends_on = classify_claim_type(claim_text)
            claims.append({
                "number": num,
                "text": claim_text,
                "is_dependent": claim_type == "종속항",
                "depends_on": depends_on,
            })

    return claims


def split_claim_elements(claim_text: str) -> list[str]:
    """단일 청구항을 구성요소로 1차 분리.

    규칙:
        1. "comprising:", "포함하는", "구비하는" 등의 전환어 이후 텍스트를 대상으로
        2. 세미콜론(;)으로 분리
        3. 세미콜론이 없으면 쉼표(,) + 줄바꿈 패턴으로 시도

    Returns:
        구성요소 텍스트 리스트 (앞뒤 공백 제거)
    """
    # 전환어 이후 부분 추출
    transition = re.search(
        r"(?:comprising|including|consisting of|포함하는|구비하는|있어서)[:\s,]*(.*)",
        claim_text,
        re.DOTALL | re.IGNORECASE,
    )
    target = transition.group(1) if transition else claim_text

    # 세미콜론으로 분리
    if ";" in target:
        elements = [e.strip() for e in target.split(";") if e.strip()]
        return elements

    # 세미콜론이 없으면 줄바꿈 기준 분리
    lines = [ln.strip() for ln in target.split("\n") if ln.strip()]
    if len(lines) > 1:
        return lines

    # 분리 불가 → 전체를 하나의 요소로
    return [target.strip()] if target.strip() else []


def classify_claim_type(claim_text: str) -> tuple[str, int | None]:
    """독립항/종속항 판별.

    종속항 패턴:
        한국: "제N항에 있어서", "제N항에 따른", "제N항의"
        영문: "according to claim N", "The ... of claim N"

    Returns:
        ("독립항", None) 또는 ("종속항", 참조_청구항_번호)
    """
    # 한국어 종속항 패턴
    kr_dep = re.search(r"제\s*(\d+)\s*항에\s*(?:있어서|따른|기재된)", claim_text)
    if kr_dep:
        return ("종속항", int(kr_dep.group(1)))

    # "제N항의" 패턴 (문장 앞부분에서)
    kr_dep2 = re.search(r"^[^.]*제\s*(\d+)\s*항의", claim_text)
    if kr_dep2:
        return ("종속항", int(kr_dep2.group(1)))

    # 영문 종속항 패턴
    en_dep = re.search(r"(?:according to|of)\s+claim\s+(\d+)", claim_text, re.IGNORECASE)
    if en_dep:
        return ("종속항", int(en_dep.group(1)))

    return ("독립항", None)
