"""Q 이미지 편집기 - 이미지를 자르고, 크기를 바꾸고, 모자이크를 넣는 윈도우 데스크톱 앱."""
from __future__ import annotations

import math
import os
import sys

from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cropcore import (
    MIN_SCALE,
    PRESETS,
    WM_MARGIN,
    CropState,
    Effects,
    Region,
    apply_mosaic,
    load_image,
    load_logo,
    mosaic_blocks,
    save_cropped,
    save_resized,
)

from feedback import ask_on_exit

APP_NAME = "Q 이미지 편집기"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif")
PREVIEW_MAX = 2200  # 미리보기용 이미지 최대 변
HANDLE_HIT = 12  # 모서리 핸들 클릭 인식 범위(화면 px)
MIN_REGION_PX = 8  # 모자이크 영역 최소 크기(화면 px)

# 다크 에디터 팔레트
C_BG = "#15161a"  # 창 바탕
C_PANEL = "#1d1e23"  # 패널
C_LINE = "#2a2c33"  # 패널 테두리
C_RAISED = "#26282f"  # 입력칸/버튼
C_TEXT = "#e8e9ed"
C_MUTED = "#9096a3"
C_DIM = "#767b86"
C_ACCENT = "#3a56ff"
C_ACCENT_LIGHT = "#8fa0ff"
C_WARN = "#ffb454"

STYLE = """
* { font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; font-size: 13px; }
QMainWindow, QWidget#root, QDialog { background: #15161a; }
QWidget { color: #e8e9ed; }
QToolTip { background: #26282f; color: #e8e9ed; border: 1px solid #3a3d47; padding: 5px 8px; }
QStatusBar { background: #111215; color: #767b86; }
QStatusBar::item { border: none; }
QFrame#panel { background: #1d1e23; border: 1px solid #2a2c33; border-radius: 14px; }
QFrame#sep { background: #2a2c33; border: none; min-height: 1px; max-height: 1px; }
QLabel { background: transparent; }
QLabel#title { font-size: 12px; font-weight: bold; color: #9096a3; }
QLabel#hint { color: #767b86; font-size: 12px; }
QLabel#muted { color: #9096a3; }
QLabel#toolname { font-size: 16px; font-weight: bold; }
QLabel#toolsub { color: #8d919b; font-size: 12px; }
QLabel#info { color: #9096a3; padding: 2px 6px; }
QLabel#count { color: #767b86; }
QLabel#beta { color: #6b7080; font-size: 11px; padding-right: 10px; }
QLabel#thumb { background: #15161a; border: 1px solid #343740; border-radius: 8px; color: #6b7080; }
QLabel#warn { background: rgba(255,180,84,30); color: #ffb454; border: 1px solid rgba(255,180,84,90);
  border-radius: 8px; padding: 8px 10px; }
QPushButton { background: #26282f; border: 1px solid #343740; border-radius: 8px; padding: 7px 12px; color: #e8e9ed; }
QPushButton:hover { background: #2e3038; border-color: #444853; }
QPushButton:pressed { background: #23252b; }
QPushButton:checked { background: #3a56ff; border-color: #3a56ff; color: white; font-weight: bold; }
QPushButton:disabled { color: #5d6170; background: #202126; border-color: #2a2c33; }
QPushButton#primary { background: #3a56ff; color: white; border: none; font-weight: bold; padding: 11px; }
QPushButton#primary:hover { background: #5a72ff; }
QPushButton#primary:pressed { background: #2f47e0; }
QPushButton#primary:disabled { background: #2a3260; color: #7a82a8; }
QPushButton#ghost { background: transparent; border: 1px solid transparent; color: #b4b9c4; padding: 6px 10px; }
QPushButton#ghost:hover { background: #26282f; color: white; }
QPushButton#ghost:disabled { color: #5d6170; background: transparent; }
QPushButton#accent { background: rgba(58,86,255,38); color: #8fa0ff; border: 1px solid rgba(58,86,255,90);
  font-weight: bold; padding: 6px 12px; }
QPushButton#accent:hover { background: rgba(58,86,255,66); }
QToolButton#tool { background: transparent; border: none; border-radius: 12px; color: #9096a3; font-size: 11px; padding: 8px 0 6px 0; }
QToolButton#tool:hover { background: #26282f; color: #e8e9ed; }
QToolButton#tool:checked { background: rgba(58,86,255,44); color: #8fa0ff; font-weight: bold; }
QToolButton#gear { background: transparent; border: none; border-radius: 12px; padding: 8px; }
QToolButton#gear:hover { background: #26282f; }
QListWidget#strip { background: transparent; border: none; outline: none; }
QListWidget#strip::item { border-radius: 10px; border: 2px solid transparent; padding: 4px; color: #9096a3; }
QListWidget#strip::item:hover { background: #26282f; }
QListWidget#strip::item:selected { background: rgba(58,86,255,40); border: 2px solid #3a56ff; color: #e8e9ed; }
QComboBox, QSpinBox { background: #26282f; border: 1px solid #343740; border-radius: 8px; padding: 6px 8px;
  min-height: 20px; selection-background-color: #3a56ff; }
QComboBox:hover, QSpinBox:hover { border-color: #444853; }
QComboBox:focus, QSpinBox:focus { border-color: #3a56ff; }
QSpinBox::up-button, QSpinBox::down-button { width: 0; border: none; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #26282f; border: 1px solid #3a3d47; selection-background-color: #3a56ff;
  selection-color: white; outline: 0; padding: 4px; }
QSlider::groove:horizontal { height: 4px; background: #343740; border-radius: 2px; }
QSlider::handle:horizontal { background: white; width: 10px; height: 10px; margin: -6px 0; border-radius: 7px;
  border: 2px solid #3a56ff; }
QSlider::sub-page:horizontal { background: #3a56ff; border-radius: 2px; }
QSlider::handle:horizontal:disabled { border-color: #4a4f5c; background: #8d919b; }
QSlider::sub-page:horizontal:disabled { background: #4a4f5c; }
QScrollBar:horizontal { height: 12px; background: transparent; margin: 0; }
QScrollBar::handle:horizontal { background: #3a3d47; border-radius: 4px; min-width: 40px; margin: 3px 2px; }
QScrollBar::handle:horizontal:hover { background: #4a4f5c; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QScrollBar:vertical { width: 12px; background: transparent; margin: 0; }
QScrollBar::handle:vertical { background: #3a3d47; border-radius: 4px; min-height: 40px; margin: 2px 3px; }
QScrollBar::handle:vertical:hover { background: #4a4f5c; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QTabWidget::pane { border: none; }
QMessageBox { background: #1d1e23; }
QPushButton#chip { background: #26282f; border: 1px solid #2a2c33; border-radius: 14px; padding: 4px 10px; color: #9096a3; font-size: 12px; }
QPushButton#chip:hover { border-color: #444853; color: #e8e9ed; }
QPushButton#chip:checked { background: rgba(58,86,255,38); border: 1px solid #3a56ff; color: #8fa0ff; font-weight: normal; }
QPushButton#chip:disabled { color: #5d6170; }
QPlainTextEdit { background: #15161a; border: 1px solid #2a2c33; border-radius: 8px; padding: 6px 8px;
  selection-background-color: #3a56ff; }
QPlainTextEdit:focus { border-color: #3a56ff; }
"""


def apply_theme(app: QApplication) -> None:
    """Fusion 스타일 + 어두운 팔레트 + 스타일시트. (체크박스/화살표 같은 기본 부품도 어둡게 그려진다)"""
    app.setStyle("Fusion")
    pal = QPalette()
    roles = {
        QPalette.Window: C_BG,
        QPalette.WindowText: C_TEXT,
        QPalette.Base: C_RAISED,
        QPalette.AlternateBase: C_PANEL,
        QPalette.Text: C_TEXT,
        QPalette.Button: C_RAISED,
        QPalette.ButtonText: C_TEXT,
        QPalette.ToolTipBase: C_RAISED,
        QPalette.ToolTipText: C_TEXT,
        QPalette.Highlight: C_ACCENT,
        QPalette.HighlightedText: "#ffffff",
        QPalette.PlaceholderText: "#6b7080",
        QPalette.Link: C_ACCENT_LIGHT,
    }
    for role, col in roles.items():
        pal.setColor(role, QColor(col))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#5d6170"))
    app.setPalette(pal)
    app.setStyleSheet(STYLE)


def set_dark_titlebar(widget: QWidget) -> None:
    """Windows 10/11 에서 제목줄도 어둡게 (지원 안 되는 환경에서는 조용히 넘어간다)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        val = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (새/옛 윈도우 값)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass


def pil_to_qimage(img: Image.Image) -> QImage:
    rgba = img.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, rgba.width * 4, QImage.Format_RGBA8888)
    return qimg.copy()


class CropCanvas(QWidget):
    """이미지를 보여주는 영역. 두 가지 모드가 있다.
    - crop   : 크롭 박스 이동(드래그) / 크기(휠, 모서리)
    - mosaic : 모자이크 영역 그리기(드래그), 선택·이동·크기 조절, Delete 로 삭제
    """

    changed = Signal()  # 크롭 상태가 바뀜 (드래그, 휠)
    regions_dragging = Signal()  # 영역 편집 중 (가벼운 갱신용)
    regions_changed = Signal()  # 영역 편집이 확정됨 (미리보기 다시 만들기)
    selection_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(520, 380)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.pixmap: QPixmap | None = None
        self.state: CropState | None = None
        self.target_size: tuple[int, int] | None = None  # 확대·축소 결과 크기(미리보기용)
        self._drag_last: QPointF | None = None
        self._corner: str | None = None
        self.wm: QPixmap | None = None
        self.wm_opacity = 50
        self.wm_size = 20
        self.wm_pos = "center"
        # 모자이크 편집
        self.mode = "crop"
        self.sel: int | None = None
        self.shape = "rect"
        self._m_action: str | None = None  # draw / move / resize
        self._m_corner: str | None = None
        self._m_start: QPointF | None = None
        self._m_last: QPointF | None = None
        self._m_new: Region | None = None

    # --- 외부에서 호출 ---
    def set_watermark(self, pix: QPixmap | None, opacity: int, size: int, pos: str) -> None:
        self.wm, self.wm_opacity, self.wm_size, self.wm_pos = pix, opacity, size, pos
        self.update()

    def set_content(self, pixmap: QPixmap | None, state: CropState | None) -> None:
        if state is not self.state:
            self.sel = None
            self._m_action = None
            self._m_new = None
            self.selection_changed.emit()
        self.pixmap = pixmap
        self.state = state
        self.update()

    def set_target(self, size: tuple[int, int] | None) -> None:
        if size != self.target_size:
            self.target_size = size
            self.update()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self.pixmap = pixmap
        self.update()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._m_action = None
        self._m_new = None
        self.setCursor(Qt.CrossCursor if mode == "mosaic" else Qt.ArrowCursor)
        self.update()

    def set_shape(self, shape: str) -> None:
        self.shape = shape
        if self.state and self.sel is not None and self.sel < len(self.state.mosaics):
            self.state.mosaics[self.sel].shape = shape
            self.regions_changed.emit()
        self.update()

    def delete_selected(self) -> None:
        if self.state and self.sel is not None and self.sel < len(self.state.mosaics):
            del self.state.mosaics[self.sel]
            self.sel = None
            self.selection_changed.emit()
            self.regions_changed.emit()
            self.update()

    # --- 좌표 변환 ---
    def _display_rect(self) -> QRectF:
        if not self.state:
            return QRectF()
        m = 24
        avail_w, avail_h = self.width() - m * 2, self.height() - m * 2
        bw, bh = self.state.width, self.state.height
        if self.mode == "resize" and self.target_size:  # 확대·축소: 바꿀 크기의 모양 그대로 보여준다
            bw, bh = self.target_size
        s = min(avail_w / bw, avail_h / bh)
        w, h = bw * s, bh * s
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _crop_widget_rect(self) -> QRectF:
        d = self._display_rect()
        l, t, r, b = self.state.rect()
        k = d.width() / self.state.width
        return QRectF(d.left() + l * k, d.top() + t * k, (r - l) * k, (b - t) * k)

    def _region_widget_rect(self, r: Region) -> QRectF:
        d = self._display_rect()
        k = d.width() / self.state.width
        return QRectF(d.left() + r.x * k, d.top() + r.y * k, r.w * k, r.h * k)

    def _to_img(self, pos: QPointF) -> tuple[QPointF, float]:
        """위젯 좌표 → 원본 이미지 좌표(이미지 안으로 제한), 화면 px→원본 px 배율"""
        d = self._display_rect()
        k = self.state.width / d.width()
        x = min(max((pos.x() - d.left()) * k, 0), self.state.width)
        y = min(max((pos.y() - d.top()) * k, 0), self.state.height)
        return QPointF(x, y), k

    # --- 그리기 ---
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        bg = QPainterPath()
        bg.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.fillPath(bg, QColor("#101114"))

        if not self.pixmap or not self.state:
            self._paint_empty(p)
            return

        d = self._display_rect()
        p.drawPixmap(d, self.pixmap, QRectF(self.pixmap.rect()))

        resize_mode = self.mode == "resize"
        c = d if resize_mode else self._crop_widget_rect()  # 확대·축소는 사진 전체가 결과
        mosaic_mode = self.mode == "mosaic"
        if not resize_mode:
            # 크롭 바깥 어둡게 (모자이크 편집 중에는 덜 어둡게)
            dim = QColor(0, 0, 0, 90 if mosaic_mode else 150)
            p.fillRect(QRectF(d.left(), d.top(), d.width(), c.top() - d.top()), dim)
            p.fillRect(QRectF(d.left(), c.bottom(), d.width(), d.bottom() - c.bottom()), dim)
            p.fillRect(QRectF(d.left(), c.top(), c.left() - d.left(), c.height()), dim)
            p.fillRect(QRectF(c.right(), c.top(), d.right() - c.right(), c.height()), dim)

        # 워터마크 미리보기 (크롭 영역 하단, 저장 결과와 같은 비율)
        if self.wm and not self.wm.isNull():
            w = c.width() * self.wm_size / 100
            h = self.wm.height() * w / self.wm.width()
            if h > c.height() * 0.9:
                h = c.height() * 0.9
                w = self.wm.width() * h / self.wm.height()
            m = c.width() * WM_MARGIN
            x = {"left": c.left() + m, "right": c.right() - w - m}.get(
                self.wm_pos, c.left() + (c.width() - w) / 2
            )
            p.setOpacity(self.wm_opacity / 100)
            p.drawPixmap(QRectF(x, c.bottom() - h - m, w, h), self.wm, QRectF(self.wm.rect()))
            p.setOpacity(1.0)

        if resize_mode:
            self._paint_resize_chips(p, d)
            return

        if mosaic_mode:
            p.setPen(QPen(QColor(255, 255, 255, 140), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(c)
            self._paint_regions(p)
            return

        # 3분할 가이드
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        for i in (1, 2):
            x = c.left() + c.width() * i / 3
            y = c.top() + c.height() * i / 3
            p.drawLine(QPointF(x, c.top()), QPointF(x, c.bottom()))
            p.drawLine(QPointF(c.left(), y), QPointF(c.right(), y))

        # 테두리와 모서리 핸들
        p.setPen(QPen(QColor(C_ACCENT_LIGHT), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(c)
        p.setBrush(QColor("white"))
        p.setPen(QPen(QColor(C_ACCENT), 1.5))
        for pt in (c.topLeft(), c.topRight(), c.bottomLeft(), c.bottomRight()):
            p.drawRoundedRect(QRectF(pt.x() - 6, pt.y() - 6, 12, 12), 3, 3)

    def _paint_resize_chips(self, p: QPainter, d: QRectF) -> None:
        """확대·축소 미리보기 위의 작은 표시: 바꿀 크기 / 비율이 달라졌다는 경고."""
        if not self.target_size or not self.state:
            return
        tw, th = self.target_size
        chips = [(f"{tw} × {th} px", QColor(0, 0, 0, 170), QColor("white"))]
        if abs((tw / th) / (self.state.width / self.state.height) - 1) > 0.01:
            chips.append(("가로세로 비율이 달라져 사진이 늘어나 보여요", QColor(255, 180, 84, 235), QColor("#2a1d05")))
        f = p.font()
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        fm = p.fontMetrics()
        y = d.top() + 8
        for text, bg, fg in chips:
            w = fm.horizontalAdvance(text) + 18
            if w > d.width() - 16:
                continue  # 사진이 너무 작게 보일 때는 글자를 생략
            r = QRectF(d.left() + 8, y, w, 24)
            path = QPainterPath()
            path.addRoundedRect(r, 7, 7)
            p.fillPath(path, bg)
            p.setPen(fg)
            p.drawText(r, Qt.AlignCenter, text)
            y += 30

    def _paint_empty(self, p: QPainter) -> None:
        """이미지가 없을 때: 끌어다 놓는 영역 안내."""
        r = QRectF(self.rect()).adjusted(28, 28, -28, -28)
        p.setPen(QPen(QColor("#2f323a"), 1.5, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 14, 14)
        cx, cy = r.center().x(), r.center().y() - 34
        # 사진 모양 아이콘
        p.setPen(QPen(QColor("#4a4f5c"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawRoundedRect(QRectF(cx - 26, cy - 20, 52, 40), 7, 7)
        p.drawEllipse(QPointF(cx - 10, cy - 6), 5, 5)
        p.drawPolyline(QPolygonF([QPointF(cx - 22, cy + 16), QPointF(cx - 4, cy + 2), QPointF(cx + 6, cy + 10),
                                  QPointF(cx + 14, cy + 4), QPointF(cx + 24, cy + 14)]))
        p.setPen(QColor("#b4b9c4"))
        f = QFont(self.font())
        f.setPixelSize(16)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(r.left(), cy + 36, r.width(), 28), Qt.AlignCenter, "여기에 사진을 끌어다 놓으세요")
        f.setPixelSize(13)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#767b86"))
        p.drawText(QRectF(r.left(), cy + 66, r.width(), 24), Qt.AlignCenter, "또는 아래 '이미지 추가' 버튼을 눌러 주세요")

    def _paint_regions(self, p: QPainter) -> None:
        orange = QColor(255, 159, 26)
        items = list(enumerate(self.state.mosaics))
        if self._m_new is not None:
            items.append((-1, self._m_new))
        for i, r in items:
            rect = self._region_widget_rect(r)
            selected = i == self.sel
            p.setBrush(QColor(255, 159, 26, 45))
            p.setPen(QPen(QColor("white") if selected else orange, 2))
            if r.shape == "ellipse":
                p.drawEllipse(rect)
                if selected:
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor(255, 255, 255, 120), 1, Qt.DashLine))
                    p.drawRect(rect)
            else:
                p.drawRect(rect)
            # 번호표
            if i >= 0:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("white") if selected else orange)
                badge = QRectF(rect.left() + 2, rect.top() + 2, 18, 18)
                p.drawRoundedRect(badge, 4, 4)
                p.setPen(QColor("#1f2430"))
                p.setFont(QFont("Malgun Gothic", 8, QFont.Bold))
                p.drawText(badge, Qt.AlignCenter, str(i + 1))
            if selected:
                p.setBrush(QColor("white"))
                p.setPen(Qt.NoPen)
                for pt in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
                    p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))

    # --- 마우스 ---
    def _corner_at(self, pos: QPointF) -> str | None:
        if not self.state:
            return None
        return self._corner_of_rect(self._crop_widget_rect(), pos)

    @staticmethod
    def _corner_of_rect(rect: QRectF, pos: QPointF) -> str | None:
        corners = {
            "tl": rect.topLeft(),
            "tr": rect.topRight(),
            "bl": rect.bottomLeft(),
            "br": rect.bottomRight(),
        }
        for key, pt in corners.items():
            if abs(pos.x() - pt.x()) <= HANDLE_HIT and abs(pos.y() - pt.y()) <= HANDLE_HIT:
                return key
        return None

    @staticmethod
    def _corner_cursor(key: str):
        return Qt.SizeFDiagCursor if key in ("tl", "br") else Qt.SizeBDiagCursor

    def mousePressEvent(self, e) -> None:
        if not self.state or e.button() != Qt.LeftButton:
            return
        if self.mode == "resize":
            return
        self.setFocus()
        if self.mode == "mosaic":
            self._mosaic_press(e)
            return
        corner = self._corner_at(e.position())
        if corner:
            self._corner = corner
            self.setCursor(self._corner_cursor(corner))
        else:
            self._drag_last = e.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e) -> None:
        if not self.state or self.mode == "resize":
            return
        if self.mode == "mosaic":
            self._mosaic_move(e)
            return
        d = self._display_rect()
        k = self.state.width / d.width()  # 화면 픽셀 → 원본 픽셀
        if self._corner:
            mx = (e.position().x() - d.left()) * k
            my = (e.position().y() - d.top()) * k
            self.state.resize_from_corner(self._corner, mx, my)
            self.update()
            self.changed.emit()
        elif self._drag_last is not None:
            delta = e.position() - self._drag_last
            self._drag_last = e.position()
            self.state.move_by(delta.x() * k, delta.y() * k)
            self.update()
            self.changed.emit()
        else:
            corner = self._corner_at(e.position())
            if corner:
                self.setCursor(self._corner_cursor(corner))
            elif self._crop_widget_rect().contains(e.position()):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, e) -> None:
        if self.mode == "resize":
            return
        if self.mode == "mosaic":
            self._mosaic_release(e)
            return
        self._drag_last = None
        self._corner = None
        self.setCursor(Qt.OpenHandCursor)

    def wheelEvent(self, e) -> None:
        if not self.state or self.mode != "crop":
            return
        step = 0.05 if e.angleDelta().y() > 0 else -0.05
        self.state.set_scale(self.state.scale + step)
        self.state.touched = True
        self.update()
        self.changed.emit()

    def keyPressEvent(self, e) -> None:
        if self.mode == "mosaic" and e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(e)

    # --- 모자이크 영역 편집 ---
    def _hit_region(self, pt: QPointF) -> int | None:
        for i in range(len(self.state.mosaics) - 1, -1, -1):  # 위에 그려진 것 우선
            r = self.state.mosaics[i]
            if r.x <= pt.x() <= r.x + r.w and r.y <= pt.y() <= r.y + r.h:
                return i
        return None

    def _mosaic_press(self, e) -> None:
        pt, _k = self._to_img(e.position())
        # 1) 선택된 영역의 모서리 → 크기 조절
        if self.sel is not None and self.sel < len(self.state.mosaics):
            corner = self._corner_of_rect(
                self._region_widget_rect(self.state.mosaics[self.sel]), e.position()
            )
            if corner:
                self._m_action, self._m_corner = "resize", corner
                return
        # 2) 영역 클릭 → 선택 + 이동
        hit = self._hit_region(pt)
        if hit is not None:
            self.sel = hit
            self._m_action, self._m_last = "move", pt
            self.shape = self.state.mosaics[hit].shape
            self.selection_changed.emit()
            self.update()
            return
        # 3) 빈 곳 → 새 영역 그리기
        self.sel = None
        self.selection_changed.emit()
        self._m_action, self._m_start = "draw", pt
        self._m_new = Region(pt.x(), pt.y(), 0, 0, self.shape)
        self.update()

    def _mosaic_move(self, e) -> None:
        pt, k = self._to_img(e.position())
        st = self.state
        if self._m_action == "draw" and self._m_new is not None:
            s = self._m_start
            self._m_new.x, self._m_new.y = min(s.x(), pt.x()), min(s.y(), pt.y())
            self._m_new.w, self._m_new.h = abs(pt.x() - s.x()), abs(pt.y() - s.y())
            self.update()
        elif self._m_action == "move" and self.sel is not None:
            r = st.mosaics[self.sel]
            r.x = min(max(r.x + pt.x() - self._m_last.x(), 0), st.width - r.w)
            r.y = min(max(r.y + pt.y() - self._m_last.y(), 0), st.height - r.h)
            self._m_last = pt
            self.update()
        elif self._m_action == "resize" and self.sel is not None:
            r = st.mosaics[self.sel]
            ax = r.x + r.w if "l" in self._m_corner else r.x
            ay = r.y + r.h if "t" in self._m_corner else r.y
            r.x, r.y = min(ax, pt.x()), min(ay, pt.y())
            r.w, r.h = abs(pt.x() - ax), abs(pt.y() - ay)
            self.update()
        else:  # 호버: 커서만 바꾼다
            cursor = Qt.CrossCursor
            if self.sel is not None and self.sel < len(st.mosaics):
                corner = self._corner_of_rect(
                    self._region_widget_rect(st.mosaics[self.sel]), e.position()
                )
                if corner:
                    cursor = self._corner_cursor(corner)
                elif self._hit_region(pt) is not None:
                    cursor = Qt.SizeAllCursor
            elif self._hit_region(pt) is not None:
                cursor = Qt.SizeAllCursor
            self.setCursor(cursor)

    def _mosaic_release(self, e) -> None:
        action, self._m_action = self._m_action, None
        if not self.state or action is None:
            return
        _pt, k = self._to_img(e.position())
        min_img = MIN_REGION_PX * k  # 화면에서 너무 작은 영역은 클릭으로 간주
        if action == "draw":
            r, self._m_new = self._m_new, None
            if r is not None and r.w >= min_img and r.h >= min_img:
                self.state.mosaics.append(r)
                self.sel = len(self.state.mosaics) - 1
                self.selection_changed.emit()
                self.regions_changed.emit()
        elif self.sel is not None:
            r = self.state.mosaics[self.sel]
            if r.w < min_img or r.h < min_img:  # 너무 작아지면 최소 크기 유지
                r.w, r.h = max(r.w, min_img), max(r.h, min_img)
                r.x = min(r.x, self.state.width - r.w)
                r.y = min(r.y, self.state.height - r.h)
            self.regions_changed.emit()
        self.update()


def resource_path(*parts: str) -> str:
    """개발 중이든 PyInstaller 로 묶었든 같은 방식으로 리소스 경로를 찾는다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def app_icon() -> QIcon:
    """창 제목줄/작업표시줄 아이콘. assets 폴더가 없어도 내장 데이터로 항상 나오게 한다."""
    icon = QIcon()
    for n in (16, 24, 32, 48, 64, 128, 256):
        path = resource_path("assets", f"icon_{n}.png")
        if os.path.exists(path):
            icon.addFile(path, QSize(n, n))
    if icon.isNull():
        try:
            import base64

            from icon_data import ICON_PNG_B64

            for n, b64 in ICON_PNG_B64.items():
                pm = QPixmap()
                if pm.loadFromData(base64.b64decode(b64), "PNG"):
                    icon.addPixmap(pm)
        except Exception:
            pass
    return icon


def tool_icon(kind: str, size: int = 26) -> QIcon:
    """왼쪽 도구 막대 아이콘 (직접 그림). 꺼짐/켜짐 색을 따로 만든다."""

    def draw(color: str) -> QPixmap:
        ratio = 3
        pm = QPixmap(size * ratio, size * ratio)
        pm.setDevicePixelRatio(ratio)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        k = size / 26
        if kind == "crop":
            p.drawPolyline(QPolygonF([QPointF(7 * k, 2.5 * k), QPointF(7 * k, 19 * k), QPointF(23.5 * k, 19 * k)]))
            p.drawPolyline(QPolygonF([QPointF(2.5 * k, 7 * k), QPointF(19 * k, 7 * k), QPointF(19 * k, 23.5 * k)]))
        elif kind == "resize":
            p.drawRoundedRect(QRectF(3.5 * k, 11 * k, 11.5 * k, 11.5 * k), 2.5 * k, 2.5 * k)
            p.drawLine(QPointF(11 * k, 15 * k), QPointF(22.5 * k, 3.5 * k))
            p.drawPolyline(QPolygonF([QPointF(15.5 * k, 3.5 * k), QPointF(22.5 * k, 3.5 * k), QPointF(22.5 * k, 10.5 * k)]))
        else:  # mosaic
            p.setPen(Qt.NoPen)
            cell, gap = 6.2 * k, 1.9 * k
            for r in range(3):
                for c in range(3):
                    col = QColor(color)
                    col.setAlphaF(1.0 if (r + c) % 2 == 0 else 0.42)
                    p.setBrush(col)
                    p.drawRoundedRect(QRectF(2.2 * k + c * (cell + gap), 2.2 * k + r * (cell + gap), cell, cell), 1.4 * k, 1.4 * k)
        p.end()
        return pm

    icon = QIcon()
    off, hot, on = draw(C_MUTED), draw(C_TEXT), draw(C_ACCENT_LIGHT)
    icon.addPixmap(off, QIcon.Normal, QIcon.Off)
    icon.addPixmap(hot, QIcon.Active, QIcon.Off)
    icon.addPixmap(on, QIcon.Normal, QIcon.On)
    icon.addPixmap(on, QIcon.Active, QIcon.On)
    return icon


def gear_icon(color: str = C_MUTED, size: int = 22) -> QIcon:
    """톱니바퀴 아이콘을 직접 그린다 (글꼴에 상관없이 항상 같은 모양)."""
    ratio = 3
    pm = QPixmap(size * ratio, size * ratio)
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.transparent)
    c = size / 2
    teeth, outer, inner, hole = 8, size * 0.48, size * 0.35, size * 0.15
    step = 2 * math.pi / teeth
    path = QPainterPath()
    pts = []
    for i in range(teeth):
        a = i * step
        for r, da in ((inner, -0.50), (inner, -0.27), (outer, -0.17), (outer, 0.17), (inner, 0.27), (inner, 0.50)):
            pts.append(QPointF(c + r * math.cos(a + da * step), c + r * math.sin(a + da * step)))
    path.moveTo(pts[0])
    for pt in pts[1:]:
        path.lineTo(pt)
    path.closeSubpath()
    path.addEllipse(QPointF(c, c), hole, hole)  # 가운데 구멍 (OddEven)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawPath(path)
    p.end()
    return QIcon(pm)


class SettingsDialog(QDialog):
    """설정 팝업. 지금은 워터마크 설정이 들어 있다. [확인]을 눌러야 적용된다."""

    POSITIONS = (("하단 중앙", "center"), ("하단 왼쪽", "left"), ("하단 오른쪽", "right"))

    def __init__(self, parent: QWidget, effects: Effects, logo: QPixmap | None, start_dir: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._start_dir = start_dir
        self.wm_path = effects.wm_path

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(10)

        title = QLabel("워터마크")
        title.setObjectName("toolname")
        lay.addWidget(title)
        sub = QLabel("저장하는 사진 아래쪽에 로고를 투명하게 넣어요.")
        sub.setObjectName("muted")
        lay.addWidget(sub)

        self.chk = QCheckBox("워터마크 넣기")
        self.chk.setChecked(bool(effects.watermark and effects.wm_path))
        self.chk.toggled.connect(self._sync_enabled)
        lay.addSpacing(4)
        lay.addWidget(self.chk)

        row = QHBoxLayout()
        row.setSpacing(12)
        self.thumb = QLabel("로고 없음")
        self.thumb.setFixedSize(150, 78)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setObjectName("thumb")
        row.addWidget(self.thumb)
        col = QVBoxLayout()
        col.setSpacing(6)
        self.lbl_name = QLabel("선택된 로고 없음")
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setObjectName("muted")
        btn = QPushButton("로고 이미지 선택…")
        btn.clicked.connect(self._choose_logo)
        col.addWidget(self.lbl_name)
        col.addWidget(btn)
        col.addStretch(1)
        row.addLayout(col, 1)
        lay.addLayout(row)

        def slider_row(label: str, lo: int, hi: int, value: int) -> tuple[QSlider, QLabel]:
            r = QHBoxLayout()
            name = QLabel(label)
            name.setMinimumWidth(44)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(value)
            val = QLabel(f"{value}%")
            val.setMinimumWidth(40)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sl.valueChanged.connect(lambda v, lb=val: lb.setText(f"{v}%"))
            r.addWidget(name)
            r.addWidget(sl, 1)
            r.addWidget(val)
            lay.addLayout(r)
            return sl, val

        self.sl_opacity, _ = slider_row("투명도", 10, 100, effects.wm_opacity)
        self.sl_size, _ = slider_row("크기", 5, 60, effects.wm_size)

        prow = QHBoxLayout()
        pname = QLabel("위치")
        pname.setMinimumWidth(44)
        self.cb_pos = QComboBox()
        for label, key in self.POSITIONS:
            self.cb_pos.addItem(label, key)
        self.cb_pos.setCurrentIndex(max(0, self.cb_pos.findData(effects.wm_pos)))
        prow.addWidget(pname)
        prow.addWidget(self.cb_pos, 1)
        lay.addLayout(prow)

        hint = QLabel("배경이 투명한 PNG 로고를 권장해요.\n크기는 저장되는 사진 가로 길이 기준 %예요.")
        hint.setObjectName("hint")
        lay.addWidget(hint)

        lay.addSpacing(6)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("취소")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("확인")
        ok.setObjectName("primary")
        ok.setMinimumWidth(96)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        if logo is not None and not logo.isNull() and self.wm_path:
            self._show_logo(logo, self.wm_path)
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        on = self.chk.isChecked()
        for w in (self.sl_opacity, self.sl_size, self.cb_pos):
            w.setEnabled(on)

    def _show_logo(self, pix: QPixmap, path: str) -> None:
        self.thumb.setPixmap(pix.scaled(142, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_name.setText(os.path.basename(path))
        self.lbl_name.setToolTip(path)

    def _choose_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "로고 이미지 선택", self._start_dir, "이미지 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not path:
            return
        try:
            pix = QPixmap.fromImage(pil_to_qimage(load_logo(path)))
        except Exception as ex:
            QMessageBox.warning(self, APP_NAME, f"로고를 열 수 없어요.\n{ex}")
            return
        self.wm_path = path
        self._show_logo(pix, path)
        self.chk.setChecked(True)  # 로고를 고르면 바로 켠다

    def accept(self) -> None:
        if self.chk.isChecked() and not self.wm_path:
            QMessageBox.information(self, APP_NAME, "워터마크를 켜려면 로고 이미지를 먼저 선택해 주세요.")
            return
        super().accept()

    def values(self) -> dict:
        return {
            "watermark": self.chk.isChecked(),
            "wm_path": self.wm_path,
            "wm_opacity": self.sl_opacity.value(),
            "wm_size": self.sl_size.value(),
            "wm_pos": self.cb_pos.currentData() or "center",
        }


class MainWindow(QMainWindow):
    MODES = ("crop", "resize", "mosaic")

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1320, 820)
        self.setAcceptDrops(True)

        self.states: list[CropState] = []
        self.pixmaps: list[QPixmap] = []
        self.previews: list[Image.Image] = []
        self.effects = Effects()
        self.wm_pixmap: QPixmap | None = None
        self.settings = QSettings("ImageRatioTool", "ImageRatioTool")
        self.ratio_label = PRESETS[0][0]
        self.ratio_value = 1.0
        self.last_dir = ""
        self._used = False  # 이번 실행에서 이미지를 한 장이라도 열었는지 (종료 의견 팝업 조건)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(12)

        outer.addWidget(self._build_rail(), 0)
        outer.addWidget(self._build_center(), 1)
        outer.addWidget(self._build_inspector(), 0)

        self._select_preset(0)
        self._load_effect_settings()
        self._set_mode("crop")
        self._refresh_buttons()
        self.statusBar().showMessage("이미지를 추가해서 시작하세요.")
        self.statusBar().setSizeGripEnabled(False)
        beta = QLabel("베타 테스트 버전 · 비상업용 · 문의: cmkim84@ajunews.com")
        beta.setObjectName("beta")
        beta.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.statusBar().addPermanentWidget(beta)

    def closeEvent(self, event) -> None:  # noqa: N802
        """종료할 때 사용 의견 팝업(조건이 맞을 때만). 어떤 경우에도 종료 자체는 막지 않는다."""
        ask_on_exit(self, self.settings, self._used, on_shown=set_dark_titlebar)
        super().closeEvent(event)

    # ---------- UI 구성 ----------
    def _panel(self) -> tuple[QFrame, QVBoxLayout]:
        f = QFrame()
        f.setObjectName("panel")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        return f, lay

    def _build_rail(self) -> QFrame:
        """왼쪽 도구 막대: 자르기 / 확대·축소 / 모자이크 + 아래쪽 설정."""
        f = QFrame()
        f.setObjectName("panel")
        f.setFixedWidth(82)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)
        group = QButtonGroup(self)
        group.setExclusive(True)
        specs = (
            ("crop", "자르기", "btn_mode_crop"),
            ("resize", "확대·축소", "btn_mode_resize"),
            ("mosaic", "모자이크", "btn_mode_mosaic"),
        )
        for kind, label, attr in specs:
            b = QToolButton()
            b.setObjectName("tool")
            b.setText(label)
            b.setIcon(tool_icon(kind))
            b.setIconSize(QSize(26, 26))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setCheckable(True)
            b.setFixedSize(66, 66)
            b.setCursor(Qt.PointingHandCursor)
            group.addButton(b)
            b.clicked.connect(lambda _=False, m=kind: self._set_mode(m))
            setattr(self, attr, b)
            lay.addWidget(b, 0, Qt.AlignHCenter)
        self.btn_mode_crop.setChecked(True)
        lay.addStretch(1)
        self.btn_settings = QToolButton()
        self.btn_settings.setObjectName("gear")
        self.btn_settings.setIcon(gear_icon())
        self.btn_settings.setIconSize(QSize(24, 24))
        self.btn_settings.setToolTip("설정")
        self.btn_settings.setCursor(Qt.PointingHandCursor)
        self.btn_settings.setFixedSize(66, 46)
        self.btn_settings.clicked.connect(self._open_settings)
        lay.addWidget(self.btn_settings, 0, Qt.AlignHCenter)
        return f

    def _build_center(self) -> QWidget:
        """가운데: 미리보기 + 안내 줄 + 아래 이미지 목록(필름스트립)."""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.canvas = CropCanvas()
        self.canvas.changed.connect(self._on_canvas_changed)
        self.canvas.regions_changed.connect(self._on_regions_changed)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        lay.addWidget(self.canvas, 1)

        self.info = QLabel("")
        self.info.setObjectName("info")
        lay.addWidget(self.info)

        strip, sl = self._panel()
        sl.setContentsMargins(12, 8, 12, 8)
        sl.setSpacing(6)
        bar = QHBoxLayout()
        bar.setSpacing(6)
        t = QLabel("이미지 목록")
        t.setObjectName("title")
        bar.addWidget(t)
        self.lbl_count = QLabel("0장")
        self.lbl_count.setObjectName("count")
        bar.addWidget(self.lbl_count)
        bar.addStretch(1)
        add = QPushButton("＋ 이미지 추가")
        add.setObjectName("accent")
        add.clicked.connect(self._add_dialog)
        rm = QPushButton("선택 삭제")
        rm.setObjectName("ghost")
        rm.clicked.connect(self._remove_current)
        clr = QPushButton("전체 비우기")
        clr.setObjectName("ghost")
        clr.clicked.connect(self._clear_all)
        for b in (add, rm, clr):
            bar.addWidget(b)
        sl.addLayout(bar)

        self.list = QListWidget()
        self.list.setObjectName("strip")
        self.list.setViewMode(QListView.IconMode)
        self.list.setFlow(QListView.LeftToRight)
        self.list.setWrapping(False)
        self.list.setMovement(QListView.Static)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setIconSize(QSize(64, 64))
        self.list.setGridSize(QSize(96, 100))
        self.list.setTextElideMode(Qt.ElideMiddle)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setFixedHeight(116)
        self.list.currentRowChanged.connect(self._on_row_changed)
        sl.addWidget(self.list)
        lay.addWidget(strip)
        return w

    def _build_inspector(self) -> QFrame:
        f, outer = self._panel()
        f.setFixedWidth(308)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        self.lbl_tool = QLabel("자르기")
        self.lbl_tool.setObjectName("toolname")
        self.lbl_tool_sub = QLabel("")
        self.lbl_tool_sub.setObjectName("toolsub")
        self.lbl_tool_sub.setWordWrap(True)
        outer.addWidget(self.lbl_tool)
        outer.addWidget(self.lbl_tool_sub)
        sep = QFrame()
        sep.setObjectName("sep")
        outer.addWidget(sep)

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.tabs.addTab(self._build_crop_tab(), "자르기")
        self.tabs.addTab(self._build_resize_tab(), "확대·축소")
        self.tabs.addTab(self._build_effects_tab(), "모자이크")
        outer.addWidget(self.tabs, 1)

        self.btn_save_one = QPushButton("현재 이미지 저장")
        self.btn_save_one.setObjectName("primary")
        self.btn_save_one.clicked.connect(self._save_current)
        self.btn_save_all = QPushButton("전체 일괄 저장")
        self.btn_save_all.setObjectName("primary")
        self.btn_save_all.clicked.connect(self._save_all)
        outer.addWidget(self.btn_save_one)
        outer.addWidget(self.btn_save_all)
        return f

    def _build_crop_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        t = QLabel("비율")
        t.setObjectName("title")
        lay.addWidget(t)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.preset_buttons: list[QPushButton] = []
        for i, (label, _w, _h) in enumerate(PRESETS):
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, idx=i: self._select_preset(idx))
            self.group.addButton(b)
            self.preset_buttons.append(b)
            grid.addWidget(b, i // 3, i % 3)
        lay.addLayout(grid)

        t2 = QLabel("직접 입력")
        t2.setObjectName("title")
        lay.addSpacing(6)
        lay.addWidget(t2)
        row = QHBoxLayout()
        self.spin_w = QSpinBox()
        self.spin_h = QSpinBox()
        for s in (self.spin_w, self.spin_h):
            s.setRange(1, 100)
            s.setValue(1)
            s.setAlignment(Qt.AlignCenter)
        self.spin_w.valueChanged.connect(self._on_custom_changed)
        self.spin_h.valueChanged.connect(self._on_custom_changed)
        row.addWidget(self.spin_w)
        row.addWidget(QLabel(":"))
        row.addWidget(self.spin_h)
        lay.addLayout(row)

        t3 = QLabel("크롭 크기")
        t3.setObjectName("title")
        lay.addSpacing(6)
        lay.addWidget(t3)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(MIN_SCALE * 100), 100)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self._on_slider)
        lay.addWidget(self.slider)
        hint = QLabel("미리보기에서 드래그하면 위치,\n마우스 휠을 굴리면 크기가 바뀌어요.")
        hint.setObjectName("hint")
        lay.addWidget(hint)

        reset = QPushButton("이 이미지 위치 초기화")
        reset.clicked.connect(self._reset_current)
        lay.addWidget(reset)

        t4 = QLabel("출력 크기 (px)")
        t4.setObjectName("title")
        lay.addSpacing(6)
        lay.addWidget(t4)
        prow = QHBoxLayout()
        self.px_w = QSpinBox()
        self.px_h = QSpinBox()
        for s in (self.px_w, self.px_h):
            s.setRange(1, 20000)
            s.setValue(1080)
            s.setAlignment(Qt.AlignCenter)
            s.valueChanged.connect(self._on_px_changed)
        prow.addWidget(self.px_w)
        prow.addWidget(QLabel("×"))
        prow.addWidget(self.px_h)
        lay.addLayout(prow)
        self.chk_px = QCheckBox("이 크기로 변환해서 저장")
        self.chk_px.toggled.connect(self._on_px_toggled)
        lay.addWidget(self.chk_px)

        lay.addStretch(1)
        return page

    # ---------- 이미지 추가/삭제 ----------
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        self.add_paths(paths)

    def _add_dialog(self) -> None:
        exts = " ".join(f"*{x}" for x in IMAGE_EXTS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "이미지 선택", self.last_dir, f"이미지 ({exts})"
        )
        self.add_paths(paths)

    def add_paths(self, paths: list[str]) -> None:
        expanded: list[str] = []
        for p in paths:
            if os.path.isdir(p):
                expanded += [
                    os.path.join(p, n) for n in sorted(os.listdir(p))
                ]
            else:
                expanded.append(p)
        added, failed = 0, []
        existing = {s.path for s in self.states}
        first_new = len(self.states)
        for p in expanded:
            if not p.lower().endswith(IMAGE_EXTS) or p in existing:
                continue
            try:
                img = load_image(p)
                self._append_image(p, img)
                added += 1
            except Exception:
                failed.append(os.path.basename(p))
        if added:
            self._used = True
            self.last_dir = os.path.dirname(expanded[0])
            self.list.setCurrentRow(first_new)
            self.statusBar().showMessage(f"{added}장을 추가했어요.")
        if failed:
            QMessageBox.warning(self, APP_NAME, "열 수 없는 파일:\n" + "\n".join(failed))
        self._refresh_buttons()

    def _append_image(self, path: str, img: Image.Image) -> None:
        state = CropState(path, img.width, img.height)
        state.set_ratio(self.ratio_value)

        preview = img.copy()
        preview.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
        pm = QPixmap.fromImage(pil_to_qimage(preview))
        icon_src = img.copy()
        icon_src.thumbnail((112, 112))
        icon = QIcon(QPixmap.fromImage(pil_to_qimage(icon_src)))

        if not self.states:  # 첫 이미지: 확대·축소 입력칸을 그 크기로 채워 둔다
            for sp, v in ((self.rz_w, img.width), (self.rz_h, img.height)):
                sp.blockSignals(True)
                sp.setValue(v)
                sp.blockSignals(False)
        self.states.append(state)
        self.pixmaps.append(pm)
        self.previews.append(preview)
        item = QListWidgetItem(icon, os.path.basename(path))
        item.setToolTip(path)
        item.setSizeHint(QSize(92, 96))
        self.list.addItem(item)

    def _remove_current(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        self.list.takeItem(row)
        del self.states[row]
        del self.pixmaps[row]
        del self.previews[row]
        if not self.states:
            self._show(None)
        self._refresh_buttons()

    def _clear_all(self) -> None:
        self.list.clear()
        self.states.clear()
        self.pixmaps.clear()
        self.previews.clear()
        self._show(None)
        self._refresh_buttons()

    # ---------- 비율/크롭 조작 ----------
    @property
    def out_size(self) -> tuple[int, int] | None:
        if self.chk_px.isChecked():
            return self.px_w.value(), self.px_h.value()
        return None

    def _set_px_checked(self, on: bool) -> None:
        self.chk_px.blockSignals(True)
        self.chk_px.setChecked(on)
        self.chk_px.blockSignals(False)

    def _clear_preset_checks(self) -> None:
        self.group.setExclusive(False)
        for b in self.preset_buttons:
            b.setChecked(False)
        self.group.setExclusive(True)

    def _on_px_changed(self) -> None:
        # 숫자를 입력하면 자동으로 px 지정 모드를 켠다
        if not self.chk_px.isChecked():
            self.chk_px.setChecked(True)  # toggled 시그널이 _apply_px 호출
        else:
            self._apply_px()

    def _on_px_toggled(self, on: bool) -> None:
        if on:
            self._apply_px()
        else:
            self._on_custom_changed()  # 비율 모드로 복귀

    def _apply_px(self) -> None:
        w, h = self.px_w.value(), self.px_h.value()
        self._clear_preset_checks()
        self._apply_ratio(f"{w}x{h}", w / h)

    def _select_preset(self, idx: int) -> None:
        label, w, h = PRESETS[idx]
        self._set_px_checked(False)
        self.preset_buttons[idx].setChecked(True)
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        self.spin_w.setValue(w)
        self.spin_h.setValue(h)
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)
        self._apply_ratio(label, w / h)

    def _on_custom_changed(self) -> None:
        w, h = self.spin_w.value(), self.spin_h.value()
        self._set_px_checked(False)
        # 프리셋과 같은 값이면 해당 프리셋 버튼을 켜고, 아니면 모두 끈다
        match = next((i for i, (_l, pw, ph) in enumerate(PRESETS) if pw == w and ph == h), None)
        self._clear_preset_checks()
        if match is not None:
            self.preset_buttons[match].setChecked(True)
        self._apply_ratio(f"{w}:{h}", w / h)

    def _apply_ratio(self, label: str, value: float) -> None:
        self.ratio_label = label
        self.ratio_value = value
        for s in self.states:
            s.set_ratio(value)
        self._sync_view()

    def _on_slider(self, v: int) -> None:
        st = self._current()
        if st:
            st.set_scale(v / 100)
            st.touched = True
            self.canvas.update()
            self._update_info()

    def _on_canvas_changed(self) -> None:
        self._sync_slider()
        self._update_info()

    def _reset_current(self) -> None:
        st = self._current()
        if st:
            st.cx = st.cy = 0.5
            st.scale = 1.0
            st.touched = False
            st.clamp()
            self._sync_view()

    # ---------- 화면 동기화 ----------
    def _current(self) -> CropState | None:
        row = self.list.currentRow()
        return self.states[row] if 0 <= row < len(self.states) else None

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self.states):
            self._show(row)

    def _show(self, row: int | None) -> None:
        if row is None:
            self.canvas.set_content(None, None)
            self.info.setText("")
            self._update_resize_ui()
            return
        self.canvas.set_content(self._preview_pixmap(row), self.states[row])
        self._sync_slider()
        self._sync_lock_fields()
        self._update_resize_ui()

    def _sync_view(self) -> None:
        row = self.list.currentRow()
        self._show(row if row >= 0 else None)

    def _sync_slider(self) -> None:
        st = self._current()
        if st:
            self.slider.blockSignals(True)
            self.slider.setValue(round(st.scale * 100))
            self.slider.blockSignals(False)

    def _update_info(self) -> None:
        st = self._current()
        if not st:
            self.info.setText("")
            return
        self._update_regions_label()
        self.info.setStyleSheet("")
        if self.canvas.mode == "resize":
            w, h = self.resize_target
            txt = f"원본 {st.width}×{st.height}px  →  변경 {w}×{h}px"
            if w > st.width or h > st.height:
                txt += "   ⚠ 원본보다 크게 늘리면 사진이 흐려지거나 깨질 수 있어요"
                self.info.setStyleSheet(f"color:{C_WARN}; font-weight:bold; padding:2px 6px;")
            self.info.setText(txt)
            return
        if self.canvas.mode == "mosaic":
            n = len(st.mosaics)
            self.info.setText(f"모자이크 영역 편집 중 · 이 이미지 {n}개 · 빈 곳을 드래그해서 영역을 추가하세요")
            return
        l, t, r, b = st.rect()
        cw, ch = round(r - l), round(b - t)
        if self.out_size:
            ow, oh = self.out_size
            self.info.setText(
                f"원본 {st.width}×{st.height}px  →  크롭 {cw}×{ch}px  →  저장 {ow}×{oh}px"
            )
        else:
            self.info.setText(
                f"원본 {st.width}×{st.height}px  →  결과 {cw}×{ch}px  ({self.ratio_label})"
            )

    def _refresh_buttons(self) -> None:
        has = bool(self.states)
        self.btn_save_one.setEnabled(has)
        self.btn_save_all.setEnabled(has)
        n = len(self.states)
        self.lbl_count.setText(f"{n}장")
        self.btn_save_all.setText(f"전체 일괄 저장 ({n}장)" if n else "전체 일괄 저장")

    # ---------- 확대·축소 ----------
    def _build_resize_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        t = QLabel("바꿀 크기 (px)")
        t.setObjectName("title")
        lay.addWidget(t)
        row = QHBoxLayout()
        self.rz_w = QSpinBox()
        self.rz_h = QSpinBox()
        for sp in (self.rz_w, self.rz_h):
            sp.setRange(1, 20000)
            sp.setValue(1000)
            sp.setAlignment(Qt.AlignCenter)
        self.rz_w.valueChanged.connect(lambda _v: self._on_rz_edited("w"))
        self.rz_h.valueChanged.connect(lambda _v: self._on_rz_edited("h"))
        self._rz_basis = "w"  # 비율 유지 때 기준이 되는 쪽(마지막에 직접 고친 칸)
        row.addWidget(self.rz_w)
        row.addWidget(QLabel("×"))
        row.addWidget(self.rz_h)
        lay.addLayout(row)
        cap = QHBoxLayout()
        cw, ch = QLabel("가로"), QLabel("세로")
        for lb in (cw, ch):
            lb.setObjectName("hint")
        cw.setAlignment(Qt.AlignCenter)
        ch.setAlignment(Qt.AlignCenter)
        cap.addWidget(cw)
        cap.addSpacing(20)
        cap.addWidget(ch)
        lay.addLayout(cap)

        self.chk_rz_lock = QCheckBox("사진 비율 유지")
        self.chk_rz_lock.setToolTip("한쪽만 입력하면 다른 쪽은 사진 비율대로 자동 계산돼요")
        self.chk_rz_lock.toggled.connect(self._on_rz_lock)
        lay.addWidget(self.chk_rz_lock)

        self.lbl_rz_orig = QLabel("")
        self.lbl_rz_orig.setObjectName("muted")
        lay.addWidget(self.lbl_rz_orig)
        self.btn_rz_orig = QPushButton("이 이미지 원본 크기 넣기")
        self.btn_rz_orig.clicked.connect(self._resize_to_original)
        lay.addWidget(self.btn_rz_orig)

        self.lbl_rz_warn = QLabel("")
        self.lbl_rz_warn.setWordWrap(True)
        self.lbl_rz_warn.setObjectName("warn")
        self.lbl_rz_warn.hide()
        lay.addWidget(self.lbl_rz_warn)

        hint = QLabel(
            "가로·세로를 입력한 그대로 사진 전체를\n늘리거나 줄여요. (자르지 않아요)\n"
            "숫자를 바꾸면 가운데 화면의 사진 모양이\n바로 바뀌어요. 비율이 달라지면 찌그러져 보여요.\n\n"
            "'사진 비율 유지'를 켜면 한쪽만 쓰세요. 다른 쪽은\n"
            "사진마다 비율대로 자동으로 정해져요.\n\n"
            "이 탭에서 저장하면 확대·축소로 저장돼요."
        )
        hint.setObjectName("hint")
        lay.addWidget(hint)
        lay.addStretch(1)
        return page

    def target_for(self, st: CropState) -> tuple[int, int]:
        """이 사진을 바꿀 크기. 비율 유지가 켜져 있으면 기준 한쪽만 쓰고 나머지는 사진 비율로 계산."""
        w, h = self.rz_w.value(), self.rz_h.value()
        if self.chk_rz_lock.isChecked():
            if self._rz_basis == "w":
                return w, max(1, round(w * st.height / st.width))
            return max(1, round(h * st.width / st.height)), h
        return w, h

    @property
    def resize_target(self) -> tuple[int, int]:
        st = self._current()
        return self.target_for(st) if st else (self.rz_w.value(), self.rz_h.value())

    def _sync_lock_fields(self) -> None:
        """비율 유지일 때, 보고 있는 사진 기준으로 반대쪽 칸의 숫자를 맞춘다."""
        st = self._current()
        if not st or not self.chk_rz_lock.isChecked():
            return
        w, h = self.target_for(st)
        for sp, v in ((self.rz_w, w), (self.rz_h, h)):
            sp.blockSignals(True)
            sp.setValue(min(v, sp.maximum()))
            sp.blockSignals(False)

    def _on_rz_edited(self, which: str) -> None:
        self._rz_basis = which
        self._sync_lock_fields()
        self._update_resize_ui()

    def _on_rz_lock(self, _on: bool) -> None:
        self._sync_lock_fields()
        self._update_resize_ui()

    def _resize_to_original(self) -> None:
        st = self._current()
        if st:
            self.rz_w.setValue(st.width)  # 값이 바뀔 때마다 UI 갱신 신호가 간다
            self.rz_h.setValue(st.height)

    def _update_resize_ui(self, *_args) -> None:
        st = self._current()
        w, h = self.resize_target
        self.canvas.set_target((w, h) if st else None)
        self.lbl_rz_orig.setText(f"이 이미지 원본: {st.width} × {st.height} px" if st else "")
        self.btn_rz_orig.setEnabled(st is not None)
        bigger = [x for x in self.states if any(a > b for a, b in zip(self.target_for(x), (x.width, x.height)))]
        lines = []
        if st and st in bigger:
            lines.append(f"⚠ 원본({st.width}×{st.height}px)보다 크게 늘리면 사진이 흐려지거나 깨져 보일 수 있어요.")
        if len(self.states) > 1 and bigger:
            lines.append(f"전체 {len(self.states)}장 중 {len(bigger)}장이 원본보다 커져요.")
        self.lbl_rz_warn.setText("\n".join(lines))
        self.lbl_rz_warn.setVisible(bool(lines))
        self._update_info()

    # ---------- 효과 (모자이크 / 워터마크) ----------
    def _build_effects_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        def title(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setObjectName("title")
            return lb

        def slider_row(label: str, lo: int, hi: int) -> tuple[QSlider, QLabel, QHBoxLayout]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            sl = QSlider(Qt.Horizontal)
            sl.setRange(lo, hi)
            val = QLabel("")
            val.setMinimumWidth(36)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(sl, 1)
            row.addWidget(val)
            return sl, val, row

        lay.addWidget(title("모자이크"))
        self.chk_mosaic = QCheckBox("모자이크 적용 (끄면 원본 그대로)")
        lay.addWidget(self.chk_mosaic)

        srow = QHBoxLayout()
        srow.addWidget(QLabel("모양"))
        self.shape_group = QButtonGroup(self)
        self.shape_buttons = {}
        for label, key in (("사각형", "rect"), ("원형", "ellipse")):
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self._on_shape(k))
            self.shape_group.addButton(b)
            self.shape_buttons[key] = b
            srow.addWidget(b, 1)
        self.shape_buttons["rect"].setChecked(True)
        lay.addLayout(srow)

        self.sl_mosaic, self.lb_mosaic, row = slider_row("강도", 1, 10)
        lay.addLayout(row)
        self.lbl_regions = QLabel("영역: 0개")
        self.lbl_regions.setObjectName("hint")
        lay.addWidget(self.lbl_regions)
        drow = QHBoxLayout()
        self.btn_del_region = QPushButton("선택 삭제")
        self.btn_del_region.clicked.connect(lambda: self.canvas.delete_selected())
        self.btn_clear_regions = QPushButton("이 이미지 전체 삭제")
        self.btn_clear_regions.clicked.connect(self._clear_regions)
        drow.addWidget(self.btn_del_region)
        drow.addWidget(self.btn_clear_regions)
        lay.addLayout(drow)
        mh = QLabel("사진 위에서\n· 빈 곳 드래그: 새 영역 추가\n· 영역 클릭: 선택 / 드래그: 이동\n· 모서리 드래그: 크기 / Delete: 삭제")
        mh.setObjectName("hint")
        lay.addWidget(mh)

        lay.addStretch(1)
        tip = QLabel("워터마크는 왼쪽 아래 톱니바퀴(설정)에서\n켜고 끌 수 있어요.")
        tip.setObjectName("hint")
        lay.addWidget(tip)

        self.chk_mosaic.toggled.connect(self._on_effects_changed)
        self.sl_mosaic.valueChanged.connect(self._on_effects_changed)
        return page

    def _load_effect_settings(self) -> None:
        st = self.settings
        for w in (self.chk_mosaic, self.sl_mosaic):
            w.blockSignals(True)
        self.chk_mosaic.setChecked(st.value("mosaic", True, type=bool))
        self.sl_mosaic.setValue(st.value("mosaic_strength", 5, type=int))
        for w in (self.chk_mosaic, self.sl_mosaic):
            w.blockSignals(False)
        e = self.effects
        e.watermark = st.value("wm", False, type=bool)
        e.wm_opacity = st.value("wm_opacity", 50, type=int)
        e.wm_size = st.value("wm_size", 20, type=int)
        e.wm_pos = st.value("wm_pos", "center", type=str)
        path = st.value("wm_path", "", type=str)
        e.wm_path = ""
        if path and os.path.exists(path):
            self._set_logo(path, warn=False)
        if not e.wm_path:
            e.watermark = False
        self._on_effects_changed()

    def _set_logo(self, path: str, warn: bool) -> bool:
        try:
            logo = load_logo(path)
        except Exception as ex:
            if warn:
                QMessageBox.warning(self, APP_NAME, f"로고를 열 수 없어요.\n{ex}")
            return False
        self.wm_pixmap = QPixmap.fromImage(pil_to_qimage(logo))
        self.effects.wm_path = path
        return True

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self.effects, self.wm_pixmap, self.last_dir)
        if dlg.exec() != QDialog.Accepted:
            return
        v = dlg.values()
        e = self.effects
        if v["wm_path"] and v["wm_path"] != e.wm_path and not self._set_logo(v["wm_path"], warn=True):
            return
        e.watermark = v["watermark"]
        e.wm_opacity = v["wm_opacity"]
        e.wm_size = v["wm_size"]
        e.wm_pos = v["wm_pos"]
        self._on_effects_changed()

    def _on_effects_changed(self, *_args) -> None:
        e = self.effects
        e.mosaic = self.chk_mosaic.isChecked()
        e.mosaic_strength = self.sl_mosaic.value()
        self.lb_mosaic.setText(str(e.mosaic_strength))
        self.sl_mosaic.setEnabled(e.mosaic)

        st = self.settings
        st.setValue("mosaic", e.mosaic)
        st.setValue("mosaic_strength", e.mosaic_strength)
        st.setValue("wm", e.watermark)
        st.setValue("wm_path", e.wm_path)
        st.setValue("wm_opacity", e.wm_opacity)
        st.setValue("wm_size", e.wm_size)
        st.setValue("wm_pos", e.wm_pos)

        # 워터마크가 켜져 있으면 톱니바퀴를 파랗게 해서 알려준다
        self.btn_settings.setIcon(gear_icon(C_ACCENT_LIGHT if e.watermark else C_MUTED))
        self.btn_settings.setToolTip("설정 (워터마크 켜짐)" if e.watermark else "설정")
        self.canvas.set_watermark(
            self.wm_pixmap if e.watermark else None, e.wm_opacity, e.wm_size, e.wm_pos
        )
        self._sync_view()

    def _preview_pixmap(self, row: int) -> QPixmap:
        st = self.states[row]
        if not self.effects.mosaic or not st.mosaics:
            return self.pixmaps[row]
        pv = self.previews[row]
        k = pv.width / st.width
        img = apply_mosaic(pv, st.mosaics, mosaic_blocks(self.effects.mosaic_strength), k)
        return QPixmap.fromImage(pil_to_qimage(img))

    def _set_mode(self, mode: str) -> None:
        self.btn_mode_crop.setChecked(mode == "crop")
        self.btn_mode_resize.setChecked(mode == "resize")
        self.btn_mode_mosaic.setChecked(mode == "mosaic")
        names = {
            "crop": ("자르기", "비율을 고르고, 사진 위에서 드래그해 위치를 맞춰요."),
            "resize": ("확대·축소", "가로·세로 크기를 숫자로 정해 사진 전체를 바꿔요."),
            "mosaic": ("모자이크", "가리고 싶은 곳을 드래그해서 영역을 만들어요."),
        }
        self.lbl_tool.setText(names[mode][0])
        self.lbl_tool_sub.setText(names[mode][1])
        self.canvas.set_mode(mode)
        self.tabs.blockSignals(True)
        self.tabs.setCurrentIndex(self.MODES.index(mode))
        self.tabs.blockSignals(False)
        self._update_info()

    def _on_regions_changed(self) -> None:
        if not self.effects.mosaic:  # 영역을 그리면 자동으로 적용을 켠다
            self.chk_mosaic.setChecked(True)  # → _on_effects_changed 가 미리보기를 다시 만든다
        else:
            row = self.list.currentRow()
            if row >= 0:
                self.canvas.set_pixmap(self._preview_pixmap(row))
        self._update_regions_label()
        self._update_info()

    def _on_selection_changed(self) -> None:
        st = self.canvas.state
        if st and self.canvas.sel is not None and self.canvas.sel < len(st.mosaics):
            self.shape_buttons[st.mosaics[self.canvas.sel].shape].setChecked(True)
        self._update_regions_label()

    def _on_shape(self, key: str) -> None:
        self.canvas.set_shape(key)

    def _clear_regions(self) -> None:
        st = self._current()
        if st and st.mosaics:
            st.mosaics.clear()
            self.canvas.sel = None
            self._on_regions_changed()

    def _update_regions_label(self) -> None:
        st = self._current()
        n = len(st.mosaics) if st else 0
        sel = self.canvas.sel
        txt = f"영역: {n}개 (현재 이미지)"
        if sel is not None and sel < n:
            txt += f" · {sel + 1}번 선택됨"
        self.lbl_regions.setText(txt)
        has_sel = sel is not None and sel < n
        self.btn_del_region.setEnabled(has_sel)
        self.btn_clear_regions.setEnabled(n > 0)

    # ---------- 저장 ----------
    def _ask_dir(self, default: str) -> str:
        return QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", default or self.last_dir)

    def _save_one(self, st: CropState, out_dir: str) -> str:
        if self.canvas.mode == "resize":
            return save_resized(st, out_dir, self.target_for(st), self.effects)
        return save_cropped(st, out_dir, self.ratio_label, self.out_size, self.effects)

    def _save_current(self) -> None:
        st = self._current()
        if not st:
            return
        out_dir = self._ask_dir(os.path.dirname(st.path))
        if not out_dir:
            return
        try:
            out = self._save_one(st, out_dir)
        except Exception as ex:
            QMessageBox.critical(self, APP_NAME, f"저장에 실패했어요.\n{ex}")
            return
        self.last_dir = out_dir
        self.statusBar().showMessage(f"저장 완료: {out}")

    def _save_all(self) -> None:
        if not self.states:
            return
        out_dir = self._ask_dir(os.path.dirname(self.states[0].path))
        if not out_dir:
            return
        ok, failed = 0, []
        for st in self.states:
            try:
                self._save_one(st, out_dir)
                ok += 1
            except Exception as ex:
                failed.append(f"{os.path.basename(st.path)}: {ex}")
        self.last_dir = out_dir
        self.statusBar().showMessage(f"{ok}장 저장 완료: {out_dir}")
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Information if not failed else QMessageBox.Warning)
        msg = f"{ok}장을 저장했어요."
        if failed:
            msg += "\n\n실패:\n" + "\n".join(failed)
        box.setText(msg)
        open_btn = box.addButton("폴더 열기", QMessageBox.ActionRole)
        box.addButton("확인", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(out_dir))


def main() -> int:
    if sys.platform == "win32":
        try:  # 작업표시줄에 파이썬이 아니라 우리 아이콘이 묶이도록
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ImageRatioTool.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(app_icon())
    apply_theme(app)
    win = MainWindow()
    win.setWindowIcon(app_icon())
    win.show()
    set_dark_titlebar(win)
    if len(sys.argv) > 1:
        win.add_paths(sys.argv[1:])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
