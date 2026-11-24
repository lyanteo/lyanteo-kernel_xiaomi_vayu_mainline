#!/bin/sh
# Pastikan setiap opsi di fragment benar-benar aktif di .config akhir.
# Pakai: check-config.sh <fragment> <.config>
frag="$1"; cfg="$2"; fail=0
grep -E '^CONFIG_' "$frag" | while IFS= read -r line; do
  key="${line%%=*}"
  if ! grep -qxF "$line" "$cfg"; then
    got=$(grep -E "^$key=|^# $key is not set" "$cfg" || echo "(tidak ada)")
    echo "GAGAL: $line  ->  $got"
    echo x >> /tmp/.cfgfail
  fi
done
if [ -s /tmp/.cfgfail ]; then n=$(wc -l < /tmp/.cfgfail); rm -f /tmp/.cfgfail; echo "$n opsi tidak aktif"; exit 1; fi
echo "Semua opsi Android aktif."
