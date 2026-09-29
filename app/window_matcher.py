from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Iterable


_BROWSER_SUFFIXES = (
    " - google chrome",
    " — google chrome",
    " - microsoft edge",
    " — microsoft edge",
    " - mozilla firefox",
    " — mozilla firefox",
)


def normalize_title(value: str) -> str:
    text = str(value or "").strip().casefold()
    for suffix in _BROWSER_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].rstrip()
            break
    text = re.sub(r"\s+", " ", text)
    return text


def _process_name(window) -> str:
    return str(getattr(window, "process_name", "") or "").strip().casefold()


def _class_name(window) -> str:
    return str(getattr(window, "class_name", "") or "").strip().casefold()


def window_match_score(saved: dict, window) -> float:
    """Nilai 0..1.5; 0 berarti kandidat sebaiknya tidak dipakai."""
    saved_title = normalize_title(saved.get("title", ""))
    current_title = normalize_title(getattr(window, "title", ""))
    saved_class = str(saved.get("class_name", "") or "").strip().casefold()
    saved_process = str(saved.get("process_name", "") or "").strip().casefold()
    current_class = _class_name(window)
    current_process = _process_name(window)

    if not saved_title or not current_title:
        return 0.0

    title_exact = saved_title == current_title
    class_match = bool(saved_class and current_class and saved_class == current_class)
    process_match = bool(saved_process and current_process and saved_process == current_process)

    # Jika workspace baru sudah punya identitas process, jangan cocokkan ke aplikasi lain.
    if saved_process and current_process and saved_process != current_process:
        return 0.0
    # Class berbeda masih mungkin terjadi setelah update aplikasi, tetapi hanya jika
    # process sama dan judulnya sangat meyakinkan.
    if saved_class and current_class and saved_class != current_class and not process_match:
        return 0.0

    if title_exact:
        score = 1.0
        if class_match:
            score += 0.20
        if process_match:
            score += 0.25
        return score

    similarity = SequenceMatcher(None, saved_title, current_title).ratio()
    token_bonus = 0.0
    saved_tokens = set(re.findall(r"[\w.-]+", saved_title))
    current_tokens = set(re.findall(r"[\w.-]+", current_title))
    if saved_tokens:
        token_bonus = 0.18 * (len(saved_tokens & current_tokens) / len(saved_tokens))

    score = similarity + token_bonus
    if class_match:
        score += 0.16
    if process_match:
        score += 0.22

    # Dengan process+class yang sama, judul boleh berubah cukup banyak, tetapi tetap
    # perlu sedikit kemiripan agar beberapa jendela Chrome tidak tertukar sembarang.
    minimum = 0.58 if (class_match or process_match) else 0.78
    return score if score >= minimum else 0.0


def find_best_window(saved: dict, windows: Iterable, used_handles: set[int] | None = None):
    used = used_handles or set()
    candidates = [w for w in windows if int(getattr(w, "handle", 0) or 0) not in used]
    if not candidates:
        return None

    scored = [(window_match_score(saved, window), window) for window in candidates]
    scored = [(score, window) for score, window in scored if score > 0]
    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best = scored[0]
        # Jika dua kandidat hampir sama kuat, jangan menebak. Retry berikutnya mungkin
        # mendapatkan title yang lebih jelas setelah aplikasi selesai loading.
        if len(scored) > 1 and abs(best_score - scored[1][0]) < 0.035:
            return None
        return best

    # Fallback aman: bila hanya ada satu window dengan process+class tersimpan,
    # gunakan itu walau judul berubah total. Jangan lakukan untuk banyak kandidat.
    saved_process = str(saved.get("process_name", "") or "").strip().casefold()
    saved_class = str(saved.get("class_name", "") or "").strip().casefold()
    if saved_process or saved_class:
        same_identity = []
        for window in candidates:
            process_ok = not saved_process or _process_name(window) == saved_process
            class_ok = not saved_class or _class_name(window) == saved_class
            if process_ok and class_ok:
                same_identity.append(window)
        if len(same_identity) == 1:
            return same_identity[0]

    return None
