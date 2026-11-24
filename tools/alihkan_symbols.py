#!/usr/bin/env python3
"""Arahkan label vendor ke node stub di tabel __symbols__ sebuah DTB.

Bootloader Qualcomm menempelkan overlay dtbo vendor dengan mencari target
lewat /__symbols__. Untuk setiap label "dtbo_X" (node stub dari patch 0007),
entri /__symbols__/X diganti agar menunjuk ke stub itu. Hasilnya overlay
vendor mendarat di node stub yang dimatikan, bukan di node mainline asli.

Kernel tidak memakai __symbols__ saat boot (hanya untuk overlay runtime),
dan referensi phandle di DTB sudah diselesaikan saat kompilasi, jadi
perubahan ini tidak mengubah perilaku kernel.

Pakai: alihkan_symbols.py file.dtb [file2.dtb ...]
"""
import subprocess
import sys


def get(dtb, *args):
    r = subprocess.run(["fdtget", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    for dtb in sys.argv[1:]:
        names = (get(dtb, "-p", dtb, "/__symbols__") or "").split()
        if not names:
            sys.exit(f"{dtb}: tidak ada /__symbols__ (build dengan DTC_FLAGS=-@)")
        done = 0
        for n in names:
            if not n.startswith("dtbo_"):
                continue
            label = n[len("dtbo_"):]
            stub = get(dtb, "-t", "s", dtb, "/__symbols__", n)
            if label not in names:
                print(f"{dtb}: label {label} tidak ada di mainline, dilewati")
                continue
            old = get(dtb, "-t", "s", dtb, "/__symbols__", label)
            subprocess.run(["fdtput", "-t", "s", dtb, "/__symbols__", label, stub], check=True)
            print(f"{dtb}: {label}: {old} -> {stub}")
            done += 1
        if done == 0:
            sys.exit(f"{dtb}: tidak ada label dtbo_* yang dialihkan")
        print(f"{dtb}: {done} label dialihkan ke stub")


if __name__ == "__main__":
    main()
