#!/usr/bin/env python3
"""Uji apakah overlay di dtbo.img vendor bisa ditempel ke DTB mainline.

Bootloader Qualcomm (ABL) memilih entri dtbo yang cocok (msm-id/board-id),
lalu menempelkannya ke DTB kernel. Kalau gagal -> boot dibatalkan -> fastboot.

Pakai: cek_dtbo.py dtbo.img base.dtb outdir [--ketat]
  --ketat: gagal juga bila overlay mengubah node di luar stub.
Butuh: fdtoverlay, fdtget, dtc (paket device-tree-compiler).
"""
import os
import struct
import subprocess
import sys

DT_TABLE_MAGIC = 0xD7B7AB1E


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def fdtget(dtb, node, prop, typ="i"):
    r = run("fdtget", "-t", typ, dtb, node, prop)
    return r.stdout.strip() if r.returncode == 0 else None


def symbols(dtb):
    r = run("fdtget", "-p", dtb, "/__symbols__")
    return set(r.stdout.split()) if r.returncode == 0 else set()


def fixups(dtbo):
    r = run("fdtget", "-p", dtbo, "/__fixups__")
    return set(r.stdout.split()) if r.returncode == 0 else set()


STUB = "/xiaomi-dtbo-compat"
IGNORE = ("/__symbols__", "/__fixups__", "/__local_fixups__")


def props(dtb):
    """{(path, prop): value} dari dtb, via dtc -O dts."""
    r = run("dtc", "-q", "-I", "dtb", "-O", "dts", "-s", dtb)
    out, stack = {}, []
    for line in r.stdout.splitlines():
        t = line.strip()
        if t.endswith("{"):
            name = t[:-1].strip().split(":")[-1].strip()
            stack.append("" if name == "/" else name)
        elif t.startswith("};"):
            if stack:
                stack.pop()
        elif t and not t.startswith(("/dts-v1/", "//", "/memreserve/")):
            path = "/" + "/".join(s for s in stack if s)
            key, _, val = t.rstrip(";").partition("=")
            out[(path, key.strip())] = val.strip()
    return out


def report_changes(base, merged):
    a, b = props(base), props(merged)
    changes = []
    for k in sorted(set(a) | set(b)):
        path = k[0]
        if path.startswith(STUB) or path.startswith(IGNORE) or "phandle" in k[1]:
            continue
        if a.get(k) != b.get(k):
            kind = "BARU" if k not in a else ("HILANG" if k not in b else "BERUBAH")
            changes.append(f"     {kind:8s} {path} : {k[1]} = {b.get(k, a.get(k))[:120]}")
    print(f"   perubahan DI LUAR node stub: {len(changes)}")
    for c in changes[:300]:
        print(c)
    return changes


def main():
    img, base, out = sys.argv[1:4]
    strict = "--ketat" in sys.argv[4:]
    os.makedirs(out, exist_ok=True)
    data = open(img, "rb").read()
    (magic, total, hsize, esize, count, eoff, psize, ver) = struct.unpack(">8I", data[:32])
    if magic != DT_TABLE_MAGIC:
        sys.exit("bukan dtbo.img (magic salah)")
    print(f"dtbo.img: {count} entri, versi {ver}")
    base_syms = symbols(base)
    base_msm = fdtget(base, "/", "qcom,msm-id")
    base_board = fdtget(base, "/", "qcom,board-id")
    print(f"DTB mainline: msm-id={base_msm} board-id={base_board} __symbols__={len(base_syms)}")
    if not base_syms:
        print("PERINGATAN: DTB mainline tidak punya __symbols__ (perlu dibuild dengan DTC_FLAGS=-@)")

    any_match = False
    all_ok = True
    outside = 0
    for i in range(count):
        off = eoff + i * esize
        (dsize, doff, eid, rev, c0, c1, c2, c3) = struct.unpack(">8I", data[off:off + 32])
        blob = data[doff:doff + dsize]
        path = os.path.join(out, f"entry{i}.dtbo")
        open(path, "wb").write(blob)
        board = fdtget(path, "/", "qcom,board-id")
        msm = fdtget(path, "/", "qcom,msm-id")
        model = fdtget(path, "/", "model", "s")
        # ABL mencocokkan board-id lengkap (platform + subtipe), mis. "47 0"
        match = board is not None and base_board is not None and board.split() == base_board.split()
        any_match |= match
        print(f"\n== entri {i}: id={eid:#x} board-id={board} msm-id={msm} model={model!r}"
              f"{'  <-- COCOK dengan board-id DTB kita' if match else ''}")
        need = fixups(path)
        missing = sorted(need - base_syms)
        print(f"   label yang dirujuk: {len(need)}, tidak ada di DTB mainline: {len(missing)}")
        for m in missing:
            print(f"     - {m}")
        present = sorted(need & base_syms)
        print(f"   label yang ADA di DTB mainline (overlay mengubah node asli): {present}")
        merged = os.path.join(out, f"hasil{i}.dtb")
        res = run("fdtoverlay", "-i", base, "-o", merged, path)
        ok = res.returncode == 0
        print(f"   fdtoverlay: {'BERHASIL' if ok else 'GAGAL'} {res.stderr.strip()}")
        if ok and match:
            outside += len(report_changes(base, merged))
        if match and not ok:
            all_ok = False
        open(os.path.join(out, f"missing{i}.txt"), "w").write("\n".join(missing) + "\n")

    print()
    if not any_match:
        print("HASIL: tidak ada entri dtbo dengan board-id yang sama -> ABL kemungkinan tidak menempelkan overlay.")
    elif all_ok and strict and outside:
        print(f"HASIL: overlay ditempel, TAPI mengubah {outside} properti di luar stub (mode ketat).")
        sys.exit(3)
    elif all_ok:
        print("HASIL: overlay vendor BERHASIL ditempel ke DTB mainline"
              + (" tanpa mengubah node mainline asli." if not outside else f" ({outside} perubahan di luar stub)."))
    else:
        print("HASIL: overlay vendor GAGAL ditempel -> ABL akan membatalkan boot (kembali ke fastboot).")
        sys.exit(2)


if __name__ == "__main__":
    main()
