#!/system/bin/sh
# Uji kernel mainline di POCO X3 Pro TANPA PC, lewat partisi RECOVERY.
# Partisi boot dan data TIDAK disentuh.
#
# Jalankan di Termux:
#   su -c "sh /sdcard/Download/tes.sh pasang"     -> backup recovery + tulis image tes
#   (matikan HP, lalu tahan Volume ATAS + Power)
#   su -c "sh /sdcard/Download/tes.sh log"        -> ambil log kernel tes
#   su -c "sh /sdcard/Download/tes.sh pulihkan"   -> kembalikan recovery asli (TWRP/OrangeFox)

set -u
DIR=/sdcard/Download
IMG=$DIR/boot-6.4-vayu-recovery.img
BACKUP=$DIR/recovery-asli-BACKUP.img
LOG=$DIR/log-kernel-tes.txt

die() { echo "GAGAL: $*"; exit 1; }

[ "$(id -u)" = "0" ] || die "jalankan dengan root: su -c \"sh $0 ...\""

PART=""
for p in /dev/block/by-name/recovery /dev/block/bootdevice/by-name/recovery \
         /dev/block/platform/soc/1d84000.ufshc/by-name/recovery; do
	[ -e "$p" ] && { PART=$p; break; }
done
[ -n "$PART" ] || die "partisi recovery tidak ditemukan"
for p in /dev/block/by-name/boot /dev/block/bootdevice/by-name/boot; do
	[ -e "$p" ] && [ "$(readlink -f "$p")" = "$(readlink -f "$PART")" ] && die "recovery menunjuk ke boot?! berhenti"
done

case "${1:-}" in
pasang)
	[ -f "$IMG" ] || die "file $IMG tidak ada (unduh dari Release dulu)"
	PSIZE=$(blockdev --getsize64 "$PART") || die "tidak bisa baca ukuran partisi"
	ISIZE=$(wc -c < "$IMG")
	echo "Partisi recovery: $PART ($PSIZE byte)"
	echo "Image tes       : $IMG ($ISIZE byte)"
	[ "$ISIZE" -lt "$PSIZE" ] || die "image lebih besar dari partisi recovery"
	if [ -f "$BACKUP" ]; then
		echo "Backup recovery sudah ada: $BACKUP (tidak ditimpa)"
	else
		echo "Membuat backup recovery asli..."
		dd if="$PART" of="$BACKUP" bs=4M 2>/dev/null || die "backup gagal"
		[ "$(wc -c < "$BACKUP")" = "$PSIZE" ] || die "ukuran backup tidak cocok"
		echo "Backup OK: $BACKUP  -> SALIN JUGA ke Google Drive/tempat lain"
	fi
	echo "Menulis image tes ke recovery..."
	dd if="$IMG" of="$PART" bs=4M conv=fsync 2>/dev/null || die "tulis gagal"
	A=$(sha256sum "$IMG" | cut -d' ' -f1)
	B=$(head -c "$ISIZE" "$PART" | sha256sum | cut -d' ' -f1)
	[ "$A" = "$B" ] || die "verifikasi gagal! jalankan: sh $0 pulihkan"
	echo
	echo "SELESAI. Langkah berikut:"
	echo " 1. Matikan HP (power off, jangan restart)."
	echo " 2. Tahan Volume ATAS + Power sampai logo POCO, lalu lepas."
	echo " 3. Perhatikan layar (foto kalau ada tulisan). Tunggu sampai HP restart sendiri."
	echo "    Kalau 3 menit tidak restart: tahan Power ~15 detik."
	echo " 4. Setelah masuk Infinity-X:  su -c \"sh $0 log\""
	echo "JANGAN pakai perintah 'reboot recovery'."
	;;
log)
	mkdir -p /sys/fs/pstore 2>/dev/null
	mount -t pstore pstore /sys/fs/pstore 2>/dev/null
	{
		echo "== isi /sys/fs/pstore =="
		ls -la /sys/fs/pstore
		for f in /sys/fs/pstore/*; do
			[ -f "$f" ] || continue
			echo; echo "===== $f ====="
			cat "$f"
		done
	} > "$LOG" 2>&1
	echo "Log disimpan di $LOG"
	if grep -q "VAYU-TES" "$LOG"; then
		echo ">>> Kernel tes TERCATAT berjalan sampai init. Baris penting:"
		grep "VAYU-TES" "$LOG" | head -n 20
	elif grep -qi "Linux version 6\." "$LOG"; then
		echo ">>> Kernel 6.x tercatat menyala tapi tidak sampai init. Kirim file log ke Claude."
	else
		echo ">>> Tidak ada jejak kernel tes di log (bisa jadi gagal sangat awal,"
		echo "    atau RAM dihapus bootloader). Kirim file log ke Claude."
	fi
	echo "Jangan lupa: su -c \"sh $0 pulihkan\""
	;;
pulihkan)
	[ -f "$BACKUP" ] || die "backup $BACKUP tidak ada"
	PSIZE=$(blockdev --getsize64 "$PART")
	[ "$(wc -c < "$BACKUP")" = "$PSIZE" ] || die "ukuran backup tidak cocok dengan partisi"
	dd if="$BACKUP" of="$PART" bs=4M conv=fsync 2>/dev/null || die "pulihkan gagal"
	A=$(sha256sum "$BACKUP" | cut -d' ' -f1)
	B=$(sha256sum "$PART" | cut -d' ' -f1)
	[ "$A" = "$B" ] || die "verifikasi pulihkan gagal, ulangi"
	echo "Recovery asli sudah dikembalikan."
	;;
*)
	echo "Pakai: su -c \"sh $0 pasang|log|pulihkan\""
	;;
esac
