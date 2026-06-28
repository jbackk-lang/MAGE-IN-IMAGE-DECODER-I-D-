def detect_rhythm(frames,
                  block_size=16,
                  thr_pulse_L=20.0,
                  thr_pulse_V=20.0,
                  thr_pulse_M=15.0,
                  min_period=2,
                  max_period=6):
    """
    RhythmAnalyzer v1 – wykrywanie pulsowania, migania, sekwencji
    - analizuje jasność (L), jasność HSV (V), ruch (M)
    - wykrywa rytmiczne zmiany w blokach obrazu
    """

    detections = []

    # Bufory poprzednich klatek
    prev_L = None
    prev_V = None
    prev_M = None

    # Bufory historii dla rytmu
    history_L = []
    history_V = []
    history_M = []

    for f in frames:
        L = f.L
        C = f.C
        M = f.M

        V = C[:, :, 2]  # jasność HSV

        # Różnice między klatkami
        dL = cv2.absdiff(L, prev_L) if prev_L is not None else None
        dV = cv2.absdiff(V, prev_V) if prev_V is not None else None
        dM = cv2.absdiff(M, prev_M) if prev_M is not None else None

        # Zapis do historii
        history_L.append(L)
        history_V.append(V)
        history_M.append(M)

        h, w = L.shape

        # Analiza blokowa
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):

                # --- Puls jasności L ---
                if dL is not None:
                    region_dL = dL[y:y+block_size, x:x+block_size]
                    pulse_L = float(np.mean(region_dL))

                    if pulse_L > thr_pulse_L:
                        detections.append(
                            Detection(
                                f.id, f.time, x, y,
                                "rhythm_light",
                                pulse_L,
                                "L",
                                "puls jasności (rytm)"
                            )
                        )

                # --- Puls jasności HSV V ---
                if dV is not None:
                    region_dV = dV[y:y+block_size, x:x+block_size]
                    pulse_V = float(np.mean(region_dV))

                    if pulse_V > thr_pulse_V:
                        detections.append(
                            Detection(
                                f.id, f.time, x, y,
                                "rhythm_color_light",
                                pulse_V,
                                "C",
                                "puls jasności HSV (rytm)"
                            )
                        )

                # --- Puls ruchu M ---
                if dM is not None:
                    region_dM = dM[y:y+block_size, x:x+block_size]
                    pulse_M = float(np.mean(region_dM))

                    if pulse_M > thr_pulse_M:
                        detections.append(
                            Detection(
                                f.id, f.time, x, y,
                                "rhythm_motion",
                                pulse_M,
                                "M",
                                "puls ruchu (rytm)"
                            )
                        )

        # aktualizacja poprzednich klatek
        prev_L = L
        prev_V = V
        prev_M = M

    return detections
