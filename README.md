# Kernel mainline 6.13 untuk POCO X3 Pro (vayu)

Kernel Linux **6.13** (sm8150-mainline) + patch khusus vayu, bukan kernel vendor 4.14.

> ⚠️ Status: **semua pemeriksaan tanpa HP lolos, tapi belum pernah dijalankan di HP sungguhan.**
> Image di sini untuk **uji sekali jalan**, bukan untuk dipakai harian.

## Hasil build

Unduh dari tab **Actions → Build kernel 6.13 vayu → run hijau terbaru → Artifacts → `kernel-6.13-vayu`**:

| File | Isi |
|---|---|
| `boot-6.13-vayu.img` | **Pakai ini dulu.** Layar memakai framebuffer dari bootloader (paling sederhana). |
| `boot-6.13-vayu-tianma.img` | Sama, tapi layar memakai driver panel Tianma buatan sendiri (eksperimen). |
| `sm8150-xiaomi-vayu*.dtb`, `kernel.config`, `SHA256SUMS` | Untuk analisis. |

Kedua image berisi initramfs kecil (busybox): menampilkan log di layar, membuka shell lewat USB
(serial ACM / telnet `172.16.42.1`), dan **tidak me-mount atau menulis partisi apa pun di HP**.

## Pemeriksaan otomatis di setiap build (build gagal kalau salah satu tidak lolos)

| Penyebab umum gagal boot | Pemeriksaan | Hasil |
|---|---|---|
| Patch tidak cocok dengan kernel | Patch diterapkan ke `v6.13.0-sm8150` asli | ✅ |
| Driver tidak bisa dikompilasi | Build lengkap `Image` + 2 DTB (clang 18) | ✅ |
| Opsi kernel penting mati | Cek 14 opsi wajib di `.config` (USB gadget, pstore, initrd, framebuffer, panel, …) | ✅ |
| Bootloader tidak memilih DTB | `qcom,msm-id <339 0x20000>`, `qcom,board-id <47 0>` sama dengan kernel vendor | ✅ |
| **Overlay `dtbo` gagal → kembali ke fastboot** | Overlay dari `dtbo.img` **asli ROM Infinity-X 3.12** ditempel ke DTB final: 126/126 label terpenuhi, **0 perubahan ke node mainline** | ✅ |
| Format boot image ditolak | Header v2, page 4096, offset, os 16.0.0 / patch 2026-09 sama dengan boot.img Infinity-X | ✅ |
| Format kernel | `Image` tidak terkompresi (magic `ARMd`), sama dengan Infinity-X | ✅ |
| Kernel crash di kode umum / init rusak | Kernel + initramfs yang sama di QEMU arm64: `vayu-initramfs: ready` tanpa panic | ✅ |

Diperiksa manual (sekali):
- Peta reserved-memory DTS vayu = kernel vendor [tejas101k/kernel_xiaomi_vayu](https://github.com/tejas101k/kernel_xiaomi_vayu) (TZ, ADSP, modem, CDSP, GPU, framebuffer, …).
- Ramoops di `0xa1600000` sama dengan kernel vendor → kalau kernel ini crash lalu HP restart, log-nya bisa dibaca dari Infinity-X: `su -c "cat /sys/fs/pstore/console-ramoops*"`.

## Yang masih belum bisa dipastikan tanpa HP

- **Perilaku hardware vayu sungguhan** (urutan clock/regulator, UFS, USB): QEMU tidak bisa meniru chip Snapdragon 860.
- Simulasi overlay memakai `fdtoverlay` (libfdt); bootloader memakai libufdt. Keduanya mengikuti format yang sama, tapi bukan kode yang identik.
- `-tianma.img`: DSC dikirim 1 slice per paket (panel vendor 2), regulator LCDB belum ada driver mainline → layar bisa rusak/hitam. Kernel tetap jalan.
- Kamera dan modem: belum ada driver open-source.

## Cara uji yang paling aman

**Butuh PC dengan fastboot.** `fastboot boot` hanya memuat kernel ke RAM sekali; tidak ada partisi yang ditulis,
tidak perlu restore, tidak perlu format.

```
fastboot boot boot-6.13-vayu.img
```

- Berhasil: log Linux bergulir di layar, lalu PC mendeteksi perangkat USB "POCO X3 Pro mainline debug".
- Gagal: HP kembali ke fastboot atau diam di logo → tahan **Power ±15 detik**, HP masuk Infinity-X seperti biasa.
  Setelah masuk Infinity-X, ambil log: `su -c "cat /sys/fs/pstore/console-ramoops*" > /sdcard/Download/log.txt`.

**Jangan** `fastboot flash`, dan **jangan** pakai menu Install/Flash Image di recovery: itu menimpa partisi boot.

## Isi repo

| Patch | Isi |
|---|---|
| `0001` | Driver touchscreen NT36672C SPI (dari port postmarketOS 6.4) |
| `0002` | Device tree `sm8150-xiaomi-vayu` (layar via framebuffer bootloader) |
| `0003` | Driver panel **Tianma 36 02 0a** (NT36672C, 1080x2400@120, DSC) + DTB `sm8150-xiaomi-vayu-tianma` |
| `0004` | Ramoops di alamat yang sama dengan kernel vendor |
| `0005` | Perbaikan driver touchscreen agar bisa dikompilasi di 6.13 |
| `0006` | `qcom,msm-id` + `qcom,board-id` dari kernel vendor |
| `0007` | Node stub untuk 126 label yang dirujuk overlay `dtbo` vendor |

| File | Isi |
|---|---|
| `vayu.config` | Opsi tambahan di atas `defconfig` + `sm8150.config` |
| `initramfs/init` | Init debug (busybox) |
| `tools/alihkan_symbols.py` | Arahkan 8 label yang juga ada di mainline (`soc`, `tlmm`, `mdss_*`, `pcie0`, `sdhc_2`, `spmi_bus`) ke stub, agar overlay vendor tidak menyentuh node asli |
| `tools/cek_dtbo.py` | Simulasi bootloader: tempel overlay `dtbo.img` ke DTB, laporkan label hilang dan perubahan di luar stub |
| `.github/workflows/build.yml` | Build + semua pemeriksaan di atas |
| `.github/workflows/cek-dtbo.yml` | Simulasi overlay saja (cepat) |

Source dasar: [sm8150-mainline/linux](https://gitlab.com/sm8150-mainline/linux) tag `v6.13.0-sm8150`.
