#!/bin/bash
# Bongkar partisi dari zip ROM menjadi folder biasa.
# Pakai: bongkar_rom.sh <rom.zip> <dir_keluar> <partisi...>
# Mendukung: payload.bin (A/B), *.new.dat.br / *.new.dat (non-A/B), *.img di dalam zip.
# Image erofs dibongkar dengan fsck.erofs, ext4 dengan debugfs.
set -euo pipefail
ZIP=$1; OUT=$2; shift 2
PARTS=("$@")
mkdir -p "$OUT/img"
W=$(mktemp -d)

isi=$(unzip -Z1 "$ZIP")
if grep -qx payload.bin <<<"$isi"; then
	echo "[bongkar] payload.bin"
	payload-dumper-go -c 4 -p "$(IFS=,; echo "${PARTS[*]}")" -o "$W" "$ZIP" >/dev/null
	for p in "${PARTS[@]}"; do [ -f "$W/$p.img" ] && mv "$W/$p.img" "$OUT/img/" || true; done
else
	for p in "${PARTS[@]}"; do
		if grep -qx "$p.new.dat.br" <<<"$isi"; then
			echo "[bongkar] $p.new.dat.br"
			unzip -q -o "$ZIP" "$p.new.dat.br" "$p.transfer.list" -d "$W"
			brotli -d -f "$W/$p.new.dat.br" -o "$W/$p.new.dat" && rm "$W/$p.new.dat.br"
			python3 /opt/sdat2img/sdat2img.py "$W/$p.transfer.list" "$W/$p.new.dat" "$OUT/img/$p.img" >/dev/null
			rm -f "$W/$p.new.dat"
		elif grep -qx "$p.new.dat" <<<"$isi"; then
			unzip -q -o "$ZIP" "$p.new.dat" "$p.transfer.list" -d "$W"
			python3 /opt/sdat2img/sdat2img.py "$W/$p.transfer.list" "$W/$p.new.dat" "$OUT/img/$p.img" >/dev/null
			rm -f "$W/$p.new.dat"
		elif f=$(grep -E "(^|/)$p\.img$" <<<"$isi" | head -n1) && [ -n "$f" ]; then
			unzip -q -o -j "$ZIP" "$f" -d "$OUT/img"
		else
			echo "[bongkar] partisi $p tidak ada di zip"
		fi
	done
fi
rm -rf "$W"

ekstrak() { # <img> <dir>
	local img=$1 dir=$2
	mkdir -p "$dir"
	if file -b "$img" | grep -qi "android sparse"; then simg2img "$img" "$img.raw" && mv "$img.raw" "$img"; fi
	# erofs: magic 0xE0F5E1E2 di offset 1024
	if [ "$(dd if="$img" bs=1 skip=1024 count=4 2>/dev/null | od -An -tx4 | tr -d ' ')" = "e0f5e1e2" ]; then
		fsck.erofs --extract="$dir" --overwrite --no-preserve "$img" >/dev/null
		echo "[bongkar] $(basename "$img"): erofs"
	else
		debugfs -R "rdump / $dir" "$img" >/dev/null 2>&1
		echo "[bongkar] $(basename "$img"): ext4"
	fi
}

for p in "${PARTS[@]}"; do
	[ -f "$OUT/img/$p.img" ] || continue
	ekstrak "$OUT/img/$p.img" "$OUT/$p"
	rm -f "$OUT/img/$p.img"
	# Partisi system-as-root: isi sebenarnya di system/system
	if [ "$p" = system ] && [ -d "$OUT/system/system" ]; then mv "$OUT/system" "$OUT/system-root"; mv "$OUT/system-root/system" "$OUT/system"; fi
	echo "[bongkar] $p: $(du -sh "$OUT/$p" | cut -f1)"
done

# Bongkar APEX sistem (berisi LLNDK/bionic/VNDK) ke $OUT/apex/<nama>
for a in $(find "$OUT"/system "$OUT"/system_ext -maxdepth 2 -path '*/apex/*' \( -name '*.apex' -o -name '*.capex' \) 2>/dev/null); do
	n=$(basename "$a"); n=${n%.*}
	T=$(mktemp -d)
	src=$a
	if [[ $a == *.capex ]]; then unzip -q -o "$a" original_apex -d "$T" && src=$T/original_apex; fi
	if unzip -q -o "$src" apex_payload.img -d "$T" 2>/dev/null; then
		ekstrak "$T/apex_payload.img" "$OUT/apex/$n" >/dev/null || true
	fi
	rm -rf "$T"
done
echo "[bongkar] apex dibongkar: $(ls "$OUT/apex" 2>/dev/null | wc -l)"
