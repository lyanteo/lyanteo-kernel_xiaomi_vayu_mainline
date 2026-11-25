#!/bin/bash
# Tiru langkah init (split SELinux policy): kompilasi kebijakan platform dari
# sistem + kebijakan vendor/odm dengan secilc. Kalau gagal di HP -> bootloop.
# Pakai: cek_sepolicy.sh <dir_sistem(s)> <dir_vendor(v)> <versi_mapping_dipakai> [ganti_versi_vendor]
#   ganti_versi_vendor: kalau diisi (mis. 202604), akhiran _202604 di cil vendor
#   diganti _<versi_mapping> (uji "turunkan versi vendor").
set -uo pipefail
S=$1; V=$2; VER=$3; DARI=${4:-}
T=$(mktemp -d)
cp "$V/vendor/etc/selinux/plat_pub_versioned.cil" "$V/vendor/etc/selinux/vendor_sepolicy.cil" "$T/"
odm=""
[ -f "$V/odm/etc/selinux/odm_sepolicy.cil" ] && cp "$V/odm/etc/selinux/odm_sepolicy.cil" "$T/" && odm="$T/odm_sepolicy.cil"
if [ -n "$DARI" ]; then
	sed -i "s/_${DARI//./_}\b/_${VER//./_}/g" "$T"/*.cil
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
if secilc -m -M true -G -N -c 30 "${args[@]}" -o "$T/policy" -f /dev/null > "$T/log" 2>&1; then
	echo "HASIL: ✅ kebijakan SELinux berhasil dikompilasi ($(stat -c %s "$T/policy") byte)"
	r=0
else
	echo "HASIL: ❌ gagal dikompilasi. Kesalahan:"
	grep -v '^$' "$T/log" | head -40
	r=1
fi
rm -rf "$T"
exit $r
