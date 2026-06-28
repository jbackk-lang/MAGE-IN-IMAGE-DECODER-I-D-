"""
i2d_core_defectscanner_v2.py — Rdzeń I²D + DefectScanner v2
Struktury danych, Layer Splitter, TwistDetector, DefectScanner v2,
SpectralOverlayDetector (podstawowy) oraz główny pipeline run_i2d().

Użycie:
    from i2d_core_defectscanner_v2 import run_i2d, Frame, Detection
    detections = run_i2d("video.mp4")
"""

import cv2
import numpy as np


# ── Struktury danych ──────────────────────────────────────────────────────────

class Frame:
    """Pojedyncza klatka z wszystkimi warstwami I²D."""

    def __init__(self, frame_id, time, raw):
        self.id   = frame_id
        self.time = time
        self.raw  = raw   # BGR (numpy array)
        self.L    = None  # jasność (grayscale)
        self.C    = None  # kolor HSV
        self.M    = None  # ruch (absdiff z poprzednią klatką)
        self.F    = None  # widmo FFT (fftshift)


class Detection:
    """Pojedyncza detekcja — wynik dowolnego modułu I²D."""

    def __init__(self, frame_id, time, x, y, dtype, strength, layer, desc):
        self.frame_id = frame_id
        self.time     = time
        self.x        = x
        self.y        = y
        self.dtype    = dtype     # typ sygnału (twist, defect, spectral_*, fusion, ...)
        self.strength = strength  # siła detekcji
        self.layer    = layer     # warstwa źródłowa (L, C, M, F)
        self.desc     = desc      # opis tekstowy


# ── Frame Loader ──────────────────────────────────────────────────────────────

def load_video(path):
    """Wczytuje wideo jako listę obiektów Frame."""
    cap = cv2.VideoCapture(path)
    frames = []
    frame_id = 0
    while True:
        ret, raw = cap.read()
        if not ret:
            break
        time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        frames.append(Frame(frame_id, time, raw))
        frame_id += 1
    cap.release()
    return frames


def load_image(path):
    """Wczytuje pojedynczy obraz statyczny jako jednoelementową listę Frame."""
    raw = cv2.imread(path)
    if raw is None:
        raise FileNotFoundError(f"Nie można wczytać obrazu: {path}")
    return [Frame(0, 0.0, raw)]


# ── Layer Splitter ────────────────────────────────────────────────────────────

def split_layers(frames):
    """
    Wypełnia warstwy L, C, M, F dla każdej klatki.

    L = jasność (grayscale)
    C = kolor (HSV)
    M = ruch (absdiff z poprzednią klatką)
    F = widmo FFT (fftshift)
    """
    prev_L = None
    for f in frames:
        f.L = cv2.cvtColor(f.raw, cv2.COLOR_BGR2GRAY)
        f.C = cv2.cvtColor(f.raw, cv2.COLOR_BGR2HSV)
        f.M = np.zeros_like(f.L) if prev_L is None else cv2.absdiff(f.L, prev_L)
        prev_L = f.L
        F = np.fft.fft2(f.L)
        f.F = np.fft.fftshift(F)


# ── TwistDetector ─────────────────────────────────────────────────────────────

def detect_twist(frames, block_size=16, threshold=20):
    """
    TwistDetector — wykrywa lokalną asymetrię / skręt w warstwie jasności L.

    Parametry:
        block_size  : rozmiar bloku analizy (px), domyślnie 16
        threshold   : próg asymetrii T > threshold → detekcja, domyślnie 20
    """
    detections = []
    for f in frames:
        L = f.L
        h, w = L.shape
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                region = L[y:y + block_size, x:x + block_size]
                if region.size == 0:
                    continue
                left   = np.mean(region[:, :block_size // 2])
                right  = np.mean(region[:, block_size // 2:])
                top    = np.mean(region[:block_size // 2, :])
                bottom = np.mean(region[block_size // 2:, :])
                T = abs(left - right) + abs(top - bottom)
                if T > threshold:
                    detections.append(
                        Detection(f.id, f.time, x, y, "twist", T, "L",
                                  "lokalna asymetria (skręt)")
                    )
    return detections


# ── DefectScanner v2 ──────────────────────────────────────────────────────────

def detect_defects(frames, block_size=16):
    """
    DefectScanner v2 — wykrywa nagłe zmiany ruchu (defekty, zniknięcia, przełączenia).

    Próg adaptacyjny: mean(M) + 2 × std(M) — zamiast stałego 25.
    Działa poprawnie zarówno na spokojnym szumie jak i przy wyraźnych defektach.
    """
    detections = []
    for f in frames:
        M = f.M
        # Próg adaptacyjny (FIX: zamiast stałego 25)
        adaptive_threshold = float(np.mean(M) + 2.0 * np.std(M))
        adaptive_threshold = max(adaptive_threshold, 10.0)  # minimum sensowny próg
        h, w = M.shape
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                region   = M[y:y + block_size, x:x + block_size]
                strength = float(np.mean(region))
                if strength > adaptive_threshold:
                    detections.append(
                        Detection(f.id, f.time, x, y, "defect", strength, "M",
                                  "nagła zmiana ruchu (defekt)")
                    )
    return detections


# ── SpectralOverlayDetector (podstawowy, bez false-positive pierścienia) ──────

def detect_spectral(frames, block_size=32, thr_multiplier=3.0):
    """
    Podstawowa detekcja anomalii widmowych w FFT.

    Nie zawiera sekcji spectral_ring (która generuje false-positive na każdej klatce
    z powodu DC-peak w centrum FFT). Zamiast tego — czyste anomalie blokowe.
    """
    detections = []
    for f in frames:
        F = np.abs(f.F)
        h, w = F.shape
        global_mean = np.mean(F)
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                region   = F[y:y + block_size, x:x + block_size]
                strength = float(np.mean(region))
                if strength > global_mean * thr_multiplier:
                    detections.append(
                        Detection(f.id, f.time, x, y, "spectral_anomaly",
                                  strength, "F",
                                  "anomalna energia widma (modulacja / nakładka)")
                    )
    return detections


# ── Pipeline I²D ──────────────────────────────────────────────────────────────

def run_i2d(path, mode="video"):
    """
    Główny pipeline I²D.

    Parametry:
        path  : ścieżka do pliku wideo lub obrazu
        mode  : "video" (domyślnie) lub "image" dla obrazów statycznych PNG/JPG

    Zwraca:
        lista Detection ze wszystkich modułów
    """
    if mode == "image":
        frames = load_image(path)
    else:
        frames = load_video(path)

    split_layers(frames)

    twist    = detect_twist(frames)
    defects  = detect_defects(frames)
    spectral = detect_spectral(frames)

    return twist + defects + spectral
