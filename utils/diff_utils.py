"""difflib 기반 텍스트 비교 유틸.

원본 청구항과 보정본의 차이를 다양한 형식으로 출력한다."""

import difflib


def generate_diff(original: str, modified: str) -> str:
    """원본과 수정본의 차이를 unified diff 형식으로 반환.

    Args:
        original: 원본 텍스트
        modified: 수정본 텍스트

    Returns:
        unified diff 문자열 (변경 없으면 빈 문자열)
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="원본",
        tofile="보정본",
        lineterm="",
    )
    return "\n".join(diff)


def generate_diff_html(original: str, modified: str) -> str:
    """원본과 수정본의 차이를 HTML 하이라이트 형식으로 반환.

    Returns:
        HTML 테이블 문자열
    """
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    differ = difflib.HtmlDiff(wrapcolumn=80)
    return differ.make_table(
        original_lines,
        modified_lines,
        fromdesc="원본",
        todesc="보정본",
    )


def get_changed_parts(original: str, modified: str) -> dict:
    """추가/삭제/변경된 부분을 분리하여 반환.

    Returns:
        {
            "added": ["추가된 문장1", ...],
            "removed": ["삭제된 문장1", ...],
            "changed": [{"from": "원본", "to": "수정본"}, ...]
        }
    """
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    sm = difflib.SequenceMatcher(None, original_lines, modified_lines)

    added = []
    removed = []
    changed = []

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "insert":
            added.extend(modified_lines[j1:j2])
        elif op == "delete":
            removed.extend(original_lines[i1:i2])
        elif op == "replace":
            # 줄 수가 같으면 변경, 다르면 삭제+추가로 처리
            orig_chunk = original_lines[i1:i2]
            mod_chunk = modified_lines[j1:j2]
            if len(orig_chunk) == len(mod_chunk):
                for o, m in zip(orig_chunk, mod_chunk):
                    changed.append({"from": o, "to": m})
            else:
                removed.extend(orig_chunk)
                added.extend(mod_chunk)

    return {"added": added, "removed": removed, "changed": changed}
