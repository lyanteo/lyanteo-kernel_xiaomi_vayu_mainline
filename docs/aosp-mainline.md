# AOSP di kernel mainline 7.x untuk Poco X3 Pro (vayu)

Proyek eksperimen: Android (AOSP) yang berjalan di atas kernel Linux mainline,
dengan grafis open-source (Mesa/freedreno), bukan blob vendor Qualcomm 4.14.

> Status: **Fase 1 (kernel)**. Belum bisa dipakai harian.
> Target realistis: tampilan, sentuh, Wi-Fi, USB/adb.
> Belum ada driver open-source untuk kamera dan modem (telepon/data).

## Fase

| Fase | Isi | Status |
|---|---|---|
| 1 | Kernel 7.x + DTS vayu + config Android (Rust Binder, cgroup, BPF, dm-verity, dll.) | Config sudah diverifikasi; workflow `kernel.yml` |
| 2 | Device tree AOSP `device/xiaomi/vayu_mainline`, berbasis target Linaro `device/linaro/dragonboard` (db845c / pixel3_mainline / beryllium) | Belum |
| 3 | HAL generik: drm_hwcomposer, minigbm (gralloc), Mesa freedreno + Turnip, audio tinyalsa, Wi-Fi ath10k | Belum |
| 4 | Build AOSP (perlu mesin besar: ±400 GB disk, 32–64 GB RAM; GitHub Actions gratis tidak cukup) | Belum |
| 5 | Uji boot di HP (`fastboot boot`, tanpa menimpa ROM) dan perbaikan bug | Belum |

## Catatan teknis

- Linux 7.x hanya punya **Rust Binder**, jadi kernel wajib dibangun dengan
  `CONFIG_RUST=y` (rustc ≥ 1.85, bindgen 0.71.1, LLVM/clang).
- iptables legacy diaktifkan karena netd Android masih memakainya.
- `kernel/check-config.sh` menggagalkan build bila ada opsi Android yang tidak aktif.
