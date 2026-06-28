import cv2
import numpy as np

# ------------------------------------------------------------
#   IMPORT MODUŁÓW I²D
# ------------------------------------------------------------

# zakładamy, że masz już:
# detect_twist
# detect_defects_v2
# detect_rhythm
# detect_color
# detect_spectral_v2
# fusion_engine

# ------------------------------------------------------------
#   REALTIME I²D
# ------------------------------------------------------------

def run_i2d_realtime(camera_id=0):
    cap = cv2.VideoCapture(camera_id)

    prev_L = None
    prev_V = None
    prev_M = None

    frame_id = 0

    while True:
        ret, raw = cap.read()
        if not ret:
            break

        time = frame_id / 30.0  # zakładamy ~30 FPS

        # --------------------------------------------
        # 1. KONSTRUKCJA KLATKI
        # --------------------------------------------
        L = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
        C = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
        V = C[:, :, 2]

        if prev_L is None:
            M = np.zeros_like(L)
        else:
            M = cv2.absdiff(L, prev_L)

        F = np.fft.fftshift(np.fft.fft2(L))

        # --------------------------------------------
        # 2. DETEKCJE MODUŁÓW
        # --------------------------------------------
        twist = detect_twist([Frame(frame_id, time, raw)])
        defects = detect_defects_v2([Frame(frame_id, time, raw)])
        rhythm = detect_rhythm([Frame(frame_id, time, raw)])
        color = detect_color([Frame(frame_id, time, raw)])
        spectral = detect_spectral_v2([Frame(frame_id, time, raw)])

        all_det = twist + defects + rhythm + color + spectral

        fusion = fusion_engine([Frame(frame_id, time, raw)], all_det)

        # --------------------------------------------
        # 3. WIZUALIZACJA NA ŻYWO
        # --------------------------------------------
        display = raw.copy()

        for d in fusion:
            cv2.rectangle(display,
                          (d.x, d.y),
                          (d.x + 16, d.y + 16),
                          (0, 0, 255),
                          2)
            cv2.putText(display,
                        d.dtype,
                        (d.x, d.y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (0, 0, 255),
                        1)

        cv2.imshow("I²D Realtime", display)

        # --------------------------------------------
        # 4. AKTUALIZACJA POPRZEDNICH KLATEK
        # --------------------------------------------
        prev_L = L
        prev_V = V
        prev_M = M

        frame_id += 1

        # --------------------------------------------
        # 5. WYJŚCIE
        # --------------------------------------------
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
