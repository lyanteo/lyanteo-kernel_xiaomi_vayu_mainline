# Kernel mainline untuk POCO X3 Pro (vayu)

Eksperimen menjalankan **kernel Linux mainline 7.x** (bukan kernel vendor 4.14) di POCO X3 Pro,
sebagai dasar AOSP dengan driver open-source (Mesa/freedreno).

> ⚠️ Status: **eksperimen, belum bisa dipakai harian.**
> Semua image di sini untuk `fastboot boot` (sekali jalan). **Jangan `fastboot flash`.**

Source kernel: [qualcomm-sm8150/linux](https://gitlab.nura.eco/soc/qualcomm-sm8150/linux)
(cadangan: [sm8150-mainline/linux](https://gitlab.com/sm8150-mainline/linux)), tag `*-sm8150` terbaru,
yang sudah memiliki device tree `sm8150-xiaomi-vayu-tianma` dan `sm8150-xiaomi-vayu-huaxing`.

## Workflow

| Workflow | Isi | Kapan jalan |
|---|---|---|
| **1 - Kernel** | Build `Image.gz`, DTB vayu, modul. Config arm64 + fragment sm8150 + fragment Android (`kernel/`). Gagal bila opsi Android wajib tidak aktif. | Push ke `kernel/**`, atau manual |
| **2 - Boot-test** | Bungkus kernel + initramfs debug (`stage1/`) jadi `boot-test-tianma.img` / `boot-test-huaxing.img`. | Otomatis setelah workflow 1 sukses, atau manual (isi Run ID workflow 1) |
| **3 - Inspeksi vendor** | Bongkar ROM Infinity-X untuk acuan format boot.img & firmware. | Manual |

Cara menguji: lihat [`stage1/CARA-TES.txt`](stage1/CARA-TES.txt).
Panel HP: cek `cat /proc/cmdline` → `j20s_36_02_0a` = **Tianma**, `j20s_42_02_0b` = **Huaxing**.

## Yang diharapkan berfungsi / tidak

- Target realistis: layar, sentuh, GPU (freedreno), USB/adb, Wi-Fi, charging.
- Belum ada driver open-source: **kamera** dan **modem (telepon/data)**.

Rencana lengkap: [`docs/aosp-mainline.md`](docs/aosp-mainline.md).
