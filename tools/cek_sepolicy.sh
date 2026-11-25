#!/bin/bash
# Tiru langkah init (split SELinux policy): kompilasi kebijakan platform dari
# sistem + kebijakan vendor/odm dengan secilc. Kalau gagal di HP -> bootloop.
# Pakai: cek_sepolicy.sh <dir_sistem(s)> <dir_vendor(v)> <versi_mapping_dipakai> [ganti_versi_vendor]
#   ganti_versi_vendor: kalau diisi (mis. 202604), akhiran _202604 di cil vendor
#   diganti _<versi_mapping> (uji "turunkan versi vendor").
# Kalau gagal, aturan vendor/odm penyebabnya dinonaktifkan satu per satu dan
# kompilasi diulang, sehingga SEMUA aturan yang tidak cocok terdaftar.
set -uo pipefail
S=$1; V=$2; VER=$3; DARI=${4:-}
T=$(mktemp -d)
cp "$V/vendor/etc/selinux/plat_pub_versioned.cil" "$V/vendor/etc/selinux/vendor_sepolicy.cil" "$T/"
odm=""
[ -f "$V/odm/etc/selinux/odm_sepolicy.cil" ] && cp "$V/odm/etc/selinux/odm_sepolicy.cil" "$T/" && odm="$T/odm_sepolicy.cil"
if [ -n "$DARI" ]; then
	sed -i "s/_${DARI//./_}\b/_${VER//./_}/g" "$T"/*.cil
fi
# BUANG (regex, opsional): buang dulu semua baris vendor/odm yang cocok,
# mis. kelas/izin yang belum ada di sistem lama (memfd_file, nlmsg).
if [ -n "${BUANG:-}" ]; then
	for f in "$T"/*.cil; do
		c=$(grep -cE "$BUANG" "$f" || true)
		[ "$c" -gt 0 ] && echo "  dibuang dari $(basename "$f"): $c baris cocok /$BUANG/"
		sed -i -E "/$BUANG/s/^/;/" "$f"
	done
fi
args=("$S/system/etc/selinux/plat_sepolicy.cil" "$S/system/etc/selinux/mapping/$VER.cil")
[ -f "$S/system/etc/selinux/mapping/$VER.compat.cil" ] && args+=("$S/system/etc/selinux/mapping/$VER.compat.cil")
for p in system_ext product; do
	for f in "$S/$p/etc/selinux/${p}_sepolicy.cil" "$S/$p/etc/selinux/mapping/$VER.cil"; do
		[ -f "$f" ] && args+=("$f")
	done
done
args+=("$T/plat_pub_versioned.cil" "$T/vendor_sepolicy.cil")
[ -n "$odm" ] && args+=("$odm")
echo "secilc dengan mapping $VER${DARI:+ (vendor $DARI diturunkan ke $VER)}:"
printf '  %s\n' "${args[@]#$S/}"

kompilasi() { secilc -m -M true -G -N -c 30 "${args[@]}" -o "$T/policy" -f /dev/null > "$T/log" 2>&1; }

: > "$T/dibuang"
n=0
until kompilasi; do
	# Kesalahan di file vendor/odm (salinan di $T) -> catat & nonaktifkan barisnya
	loc=$(grep -oE "at $T/[a-z_]+\.cil:[0-9]+" "$T/log" | head -n1)
	if [ -z "$loc" ] || [ $n -ge 400 ]; then
		echo "HASIL: ❌ gagal dikompilasi (bukan di aturan vendor, atau terlalu banyak). Kesalahan:"
		grep -v '^$' "$T/log" | head -20
		[ $n -gt 0 ] && { echo; echo "Aturan vendor/odm yang tidak cocok ($n):"; cat "$T/dibuang"; }
		rm -rf "$T"; exit 1
	fi
	f=${loc#at }; f=${f%:*}; l=${loc##*:}
	asal=$(grep -oE "from [^ ]+\.te:[0-9]+" "$T/log" | head -n1)
	echo "$(basename "$f"):$l ${asal#from } :: $(sed -n "${l}p" "$f" | cut -c1-160)" >> "$T/dibuang"
	sed -i "${l}s/^/;/" "$f"
	n=$((n+1))
done
if [ $n -eq 0 ]; then
	echo "HASIL: ✅ kebijakan SELinux berhasil dikompilasi tanpa perubahan ($(stat -c %s "$T/policy") byte)"
	r=0
else
	echo "HASIL: ⚠️ berhasil dikompilasi SETELAH $n aturan vendor/odm dinonaktifkan:"
	cat "$T/dibuang"
	echo "Tipe/atribut yang dirujuk aturan tsb tidak ada di sistem ini."
	r=2
fi
rm -rf "$T"
exit $r
