# Kernel mainline 6.13 untuk POCO X3 Pro (vayu)

Kernel Linux **6.13** (sm8150-mainline) + patch khusus vayu, bukan kernel vendor 4.14.

> ⚠️ Status: **eksperimen, belum pernah dites di HP.** Jangan flash ke HP yang dipakai harian.

## Isi

| Patch | Isi |
|---|---|
| `0001` | Driver touchscreen NT36672C SPI (dari port postmarketOS 6.4) |
| `0002` | Device tree `sm8150-xiaomi-vayu` (layar via framebuffer bootloader) |
| `0003` | Driver panel **Tianma 36 02 0a** (NT36672C, 1080x2400@120, DSC) + DTB `sm8150-xiaomi-vayu-tianma` |
| `0004` | Ramoops di alamat yang sama dengan kernel vendor → log crash bisa dibaca dari ROM Android (`/sys/fs/pstore`) |
| `0005` | Perbaikan driver touchscreen agar bisa dikompilasi di 6.13 |
| `0006` | `qcom,msm-id <339 0x20000>` + `qcom,board-id <47 0>` (dari kernel vendor) agar bootloader Qualcomm mau memilih DTB ini |
| `0007` | Node stub untuk 126 label yang dirujuk overlay `dtbo` Infinity-X, agar bootloader berhasil menempelkan overlay (kalau gagal → kembali ke fastboot). `tools/alihkan_symbols.py` mengarahkan 8 label yang juga ada di mainline (`soc`, `tlmm`, `mdss_*`, `pcie0`, `sdhc_2`, `spmi_bus`) ke stub, sehingga overlay tidak menyentuh node mainline asli |

- Source dasar: [sm8150-mainline/linux](https://gitlab.com/sm8150-mainline/linux) tag `v6.13.0-sm8150`
- `vayu.config`: opsi tambahan (panel, pstore) di atas `defconfig` + `sm8150.config`
- `initramfs/init`: busybox, buka shell lewat USB (serial ACM + telnet `172.16.42.1`)

## Build

Otomatis di GitHub Actions (**Build kernel 6.13 vayu**) setiap ada perubahan di `patches/`, `initramfs/`, atau `vayu.config`.
Hasil (artifact): `Image.gz`, DTB, boot image **header v2** (format sama dengan boot.img Infinity-X 3.12): `boot-6.13-vayu.img` (layar framebuffer, paling aman) dan `boot-6.13-vayu-tianma.img` (driver panel).

## Yang sudah diverifikasi

- Patch diterapkan bersih ke `v6.13.0-sm8150`.
- Driver touchscreen, panel, notifier DRM, dan kedua DTB lolos kompilasi.
- Peta reserved-memory DTS vayu sama dengan kernel vendor (tejas101k/kernel_xiaomi_vayu).
- msm-id/board-id sama dengan kernel vendor; format boot image (header v2, Image tidak terkompresi) sama dengan Infinity-X.
- Simulasi bootloader: overlay `dtbo.img` asli dari ROM Infinity-X 3.12 berhasil ditempel ke DTB, **tanpa mengubah node mainline** (dicek di setiap build, mode ketat).
- Kernel + initramfs yang sama boot sampai init siap di QEMU arm64.

## Risiko yang diketahui

- Panel: kernel ini mengirim DSC 1 slice per paket, panel vendor memakai 2 → gambar bisa rusak di DTB `-tianma`.
- Regulator LCDB (LAB/IBB) belum ada driver mainline → mengandalkan kondisi dari bootloader.
- Kamera dan modem belum ada driver open-source.
