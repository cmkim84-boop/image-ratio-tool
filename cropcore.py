"""크롭 계산과 저장 로직 (UI와 분리해서 테스트하기 쉽게 만든 모듈)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageOps

PRESETS = [
    ("1:1", 1, 1),
    ("4:5", 4, 5),
    ("3:4", 3, 4),
    ("2:3", 2, 3),
    ("9:16", 9, 16),
    ("4:3", 4, 3),
    ("3:2", 3, 2),
    ("16:9", 16, 9),
    ("21:9", 21, 9),
]

MIN_SCALE = 0.1


def load_image(path: str) -> Image.Image:
    """EXIF 회전을 반영해서 이미지를 연다."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img.load()
    return img


@dataclass
class Effects:
    """모자이크/워터마크 설정."""

    mosaic: bool = True  # 모자이크 영역 적용 여부
    mosaic_strength: int = 5  # 1~10, 클수록 강함
    watermark: bool = False
    wm_path: str = ""
    wm_opacity: int = 50  # 퍼센트
    wm_size: int = 20  # 출력 가로 대비 퍼센트
    wm_pos: str = "center"  # left / center / right


WM_MARGIN = 0.03  # 출력 가로 대비 여백 비율 (미리보기와 저장이 동일하게 사용)


def mosaic_blocks(strength: int) -> int:
    """영역의 짧은 변을 몇 칸으로 나눌지. 강도가 클수록 칸 수가 적어 더 뭉개진다."""
    return max(3, round(14 - 1.2 * strength))


@dataclass
class Region:
    """모자이크 영역. 원본 이미지 픽셀 좌표."""

    x: float
    y: float
    w: float
    h: float
    shape: str = "rect"  # rect / ellipse


@dataclass
class CropState:
    """이미지 한 장의 크롭 상태. 중심점은 0~1 정규화 좌표."""

    path: str
    width: int
    height: int
    cx: float = 0.5
    cy: float = 0.5
    scale: float = 1.0  # 1.0 = 비율을 유지하며 들어가는 가장 큰 크기
    ratio: float = 1.0
    touched: bool = field(default=False)  # 사용자가 직접 위치를 조절했는지
    mosaics: list = field(default_factory=list)  # 이 이미지의 모자이크 영역들

    def max_size(self) -> tuple[float, float]:
        if self.width / self.height > self.ratio:
            h = float(self.height)
            return h * self.ratio, h
        w = float(self.width)
        return w, w / self.ratio

    def rect(self) -> tuple[float, float, float, float]:
        """크롭 영역 (left, top, right, bottom) 을 원본 픽셀 좌표로 반환."""
        mw, mh = self.max_size()
        w, h = mw * self.scale, mh * self.scale
        left = min(max(self.cx * self.width - w / 2, 0), self.width - w)
        top = min(max(self.cy * self.height - h / 2, 0), self.height - h)
        return left, top, left + w, top + h

    def clamp(self) -> None:
        l, t, r, b = self.rect()
        self.cx = (l + r) / 2 / self.width
        self.cy = (t + b) / 2 / self.height

    def set_ratio(self, ratio: float) -> None:
        self.ratio = ratio
        self.clamp()

    def set_scale(self, scale: float) -> None:
        self.scale = min(max(scale, MIN_SCALE), 1.0)
        self.clamp()

    def resize_from_corner(self, corner: str, mx: float, my: float) -> None:
        """모서리(tl/tr/bl/br)를 끌어 크기 조절. 반대쪽 모서리는 고정, 비율 유지.
        mx, my 는 마우스의 원본 이미지 좌표."""
        l, t, r, b = self.rect()
        sx = -1 if "l" in corner else 1
        sy = -1 if "t" in corner else 1
        ax = r if sx < 0 else l
        ay = b if sy < 0 else t
        mw, _mh = self.max_size()

        w = max((mx - ax) * sx, (my - ay) * sy * self.ratio)
        avail_w = (self.width - ax) if sx > 0 else ax
        avail_h = (self.height - ay) if sy > 0 else ay
        w = min(w, avail_w, avail_h * self.ratio)
        w = max(w, mw * MIN_SCALE)
        h = w / self.ratio

        nl = ax if sx > 0 else ax - w
        nt = ay if sy > 0 else ay - h
        self.scale = min(max(w / mw, MIN_SCALE), 1.0)
        self.cx = (nl + w / 2) / self.width
        self.cy = (nt + h / 2) / self.height
        self.touched = True
        self.clamp()

    def move_by(self, dx_px: float, dy_px: float) -> None:
        self.cx += dx_px / self.width
        self.cy += dy_px / self.height
        self.touched = True
        self.clamp()


def crop_image(img: Image.Image, state: CropState) -> Image.Image:
    l, t, r, b = state.rect()
    box = (round(l), round(t), round(r), round(b))
    return img.crop(box)


def apply_mosaic(img: Image.Image, regions, blocks: int, k: float = 1.0) -> Image.Image:
    """영역들(원본 좌표, k 배율 적용)을 모자이크 처리한 새 이미지를 반환.
    blocks: 영역의 짧은 변을 몇 칸으로 나눌지."""
    if not regions:
        return img
    out = img.copy()
    for r in regions:
        l = max(0, int(r.x * k))
        t = max(0, int(r.y * k))
        rr = min(out.width, int(round((r.x + r.w) * k)))
        bb = min(out.height, int(round((r.y + r.h) * k)))
        rw, rh = rr - l, bb - t
        if rw < 2 or rh < 2:
            continue
        region = out.crop((l, t, rr, bb))
        bs = max(2, round(min(rw, rh) / blocks))
        small = region.resize((max(1, -(-rw // bs)), max(1, -(-rh // bs))), Image.BOX)
        pixelated = small.resize(region.size, Image.NEAREST)
        if r.shape == "ellipse":
            mask = Image.new("L", region.size, 0)
            ImageDraw.Draw(mask).ellipse([0, 0, rw - 1, rh - 1], fill=255)
            out.paste(pixelated, (l, t), mask)
        else:
            out.paste(pixelated, (l, t))
    return out


def load_logo(path: str) -> Image.Image:
    logo = Image.open(path)
    logo = ImageOps.exif_transpose(logo)
    return logo.convert("RGBA")


def apply_watermark(img: Image.Image, logo: Image.Image, opacity: int, size_pct: int, pos: str) -> Image.Image:
    """로고를 이미지 하단에 반투명으로 얹는다. 입력이 RGB면 RGB로 돌려준다."""
    base = img.convert("RGBA")
    w = max(1, round(base.width * size_pct / 100))
    h = max(1, round(logo.height * w / logo.width))
    if h > base.height * 0.9:  # 세로로 너무 긴 로고는 높이 기준으로 제한
        h = max(1, round(base.height * 0.9))
        w = max(1, round(logo.width * h / logo.height))
    mark = logo.resize((w, h), Image.LANCZOS)
    alpha = mark.getchannel("A").point(lambda a: round(a * opacity / 100))
    mark.putalpha(alpha)
    m = round(base.width * WM_MARGIN)
    x = {"left": m, "right": base.width - w - m}.get(pos, (base.width - w) // 2)
    y = base.height - h - m
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(mark, (max(0, x), max(0, y)))
    out = Image.alpha_composite(base, layer)
    return out if img.mode == "RGBA" else out.convert("RGB")


def unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"


def save_cropped(
    state: CropState,
    out_dir: str,
    ratio_label: str,
    out_size: tuple[int, int] | None = None,
    effects: Effects | None = None,
) -> str:
    """크롭해서 저장하고 저장 경로를 반환. 원본 포맷을 유지한다.
    out_size 가 있으면 크롭 결과를 정확히 그 px 크기로 리사이즈한다."""
    img = load_image(state.path)
    if effects and effects.mosaic and state.mosaics:
        img = apply_mosaic(img, state.mosaics, mosaic_blocks(effects.mosaic_strength))
    cropped = crop_image(img, state)
    if out_size and cropped.size != tuple(out_size):
        if cropped.mode == "P":
            cropped = cropped.convert("RGBA")
        cropped = cropped.resize(tuple(out_size), Image.LANCZOS)
    if effects and effects.watermark and effects.wm_path and os.path.exists(effects.wm_path):
        cropped = apply_watermark(
            cropped, load_logo(effects.wm_path), effects.wm_opacity, effects.wm_size, effects.wm_pos
        )

    return _write_image(cropped, state.path, out_dir, ratio_label)


def save_resized(
    state: CropState,
    out_dir: str,
    size: tuple[int, int],
    effects: Effects | None = None,
) -> str:
    """크롭 없이 사진 전체를 정확히 size(px)로 늘리거나 줄여서 저장한다. 비율은 무시(강제 변환)."""
    img = load_image(state.path)
    if effects and effects.mosaic and state.mosaics:
        img = apply_mosaic(img, state.mosaics, mosaic_blocks(effects.mosaic_strength))
    size = (int(size[0]), int(size[1]))
    if img.size != size:
        if img.mode == "P":
            img = img.convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
    if effects and effects.watermark and effects.wm_path and os.path.exists(effects.wm_path):
        img = apply_watermark(
            img, load_logo(effects.wm_path), effects.wm_opacity, effects.wm_size, effects.wm_pos
        )
    return _write_image(img, state.path, out_dir, f"{size[0]}x{size[1]}")


def _write_image(img: Image.Image, src_path: str, out_dir: str, label: str) -> str:
    """원본 포맷을 유지해 name_{label}.ext 로 저장 (이름이 겹치면 _2, _3 ...)."""
    name, ext = os.path.splitext(os.path.basename(src_path))
    ext = ext.lower() or ".png"
    suffix = label.replace(":", "x")
    out = unique_path(os.path.join(out_dir, f"{name}_{suffix}{ext}"))

    save_kwargs: dict = {}
    if ext in (".jpg", ".jpeg"):
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        save_kwargs = {"quality": 95, "subsampling": 0}
    elif ext == ".webp":
        save_kwargs = {"quality": 95}
    elif ext == ".bmp" and img.mode == "RGBA":
        img = img.convert("RGB")

    os.makedirs(out_dir, exist_ok=True)
    img.save(out, **save_kwargs)
    return out
