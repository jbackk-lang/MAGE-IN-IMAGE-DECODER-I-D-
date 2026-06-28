def detect_spectral_v2(frames,
                       block_size=32,
                       thr_multiplier=3.0,
                       thr_direction=2.5,
                       thr_ring=2.0):
    """
    SpectralOverlayDetector v2 – analiza widma (FFT)
    - wykrywa anomalie widmowe, siatki, wzory, modulacje, pierścienie
    - działa na FFT przesuniętym (fftshift)
    """

    detections = []

    for f in frames:
        # Widmo amplitudowe
        F = np.abs(f.F)
        h, w = F.shape

        global_mean = np.mean(F)

        # --- 1. ANOMALIE BLOKOWE ---
        for y in range(0, h, block_size):
            for x in range(0, w, block_size):
                region = F[y:y+block_size, x:x+block_size]
                strength = float(np.mean(region))

                if strength > global_mean * thr_multiplier:
                    detections.append(
                        Detection(
                            f.id, f.time, x, y,
                            "spectral_anomaly",
                            strength,
                            "F",
                            "anomalna energia widma (modulacja / nakładka)"
                        )
                    )

        # --- 2. LINIE KIERUNKOWE (siatki, krzyże, patterny) ---
        # pionowe
        vertical_profile = np.mean(F, axis=0)
        if np.max(vertical_profile) > np.mean(vertical_profile) * thr_direction:
            detections.append(
                Detection(
                    f.id, f.time, 0, 0,
                    "spectral_vertical_line",
                    float(np.max(vertical_profile)),
                    "F",
                    "silna linia pionowa w widmie (siatka / pattern)"
                )
            )

        # poziome
        horizontal_profile = np.mean(F, axis=1)
        if np.max(horizontal_profile) > np.mean(horizontal_profile) * thr_direction:
            detections.append(
                Detection(
                    f.id, f.time, 0, 0,
                    "spectral_horizontal_line",
                    float(np.max(horizontal_profile)),
                    "F",
                    "silna linia pozioma w widmie (siatka / pattern)"
                )
            )

        # --- 3. PIERŚCIENIE WIDMOWE (astronomia, kwarki, rotacja) ---
        cy = h // 2
        cx = w // 2

        # odległość od środka (mapa radialna)
        Y, X = np.ogrid[:h, :w]
        R = np.sqrt((X - cx)**2 + (Y - cy)**2)

        # radialny profil widma
        radial_bins = np.linspace(0, np.max(R), 64)
        radial_profile = []

        for i in range(len(radial_bins) - 1):
            mask = (R >= radial_bins[i]) & (R < radial_bins[i+1])
            if np.any(mask):
                radial_profile.append(np.mean(F[mask]))
            else:
                radial_profile.append(0)

        radial_profile = np.array(radial_profile)

        if np.max(radial_profile) > np.mean(radial_profile) * thr_ring:
            detections.append(
                Detection(
                    f.id, f.time, cx, cy,
                    "spectral_ring",
                    float(np.max(radial_profile)),
                    "F",
                    "pierścień widmowy (rotacja / rezonans / struktura harmoniczna)"
                )
            )

        # --- 4. PIKI HARMONICZNE (rezonanse, kwarki, modulacje) ---
        spectrum_flat = F.flatten()
        peak = np.max(spectrum_flat)

        if peak > global_mean * 4.0:
            detections.append(
                Detection(
                    f.id, f.time, cx, cy,
                    "spectral_peak",
                    float(peak),
                    "F",
                    "silny pik harmoniczny (rezonans / modulacja)"
                )
            )

    return detections
