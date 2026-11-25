#!/usr/bin/env python3
"""Cek kecocokan vendor (+odm) sebuah ROM dengan sistem Android lain.

Pemeriksaan (semuanya penyebab umum bootloop kalau vendor dan sistem beda versi):
1. VINTF: target-level manifest vendor harus ada di compatibility_matrix sistem.
2. SELinux: versi plat_sepolicy vendor harus punya file mapping di sistem.
3. Library: setiap NEEDED di vendor/odm harus ada di vendor/odm atau sistem;
   library yang diambil dari sistem harus termasuk LLNDK (selain itu diblok
   linker namespace).
4. Simbol: setiap simbol undefined (non-weak) harus diekspor library yang tersedia.

Pakai: analisis_vendor.py <vendor> <odm> <system> <laporan.md> [dir_lib_sistem_tambahan ...]
  dir tambahan: system_ext, isi APEX yang sudah dibongkar, dsb.
Butuh: pyelftools
"""
import os
import re
import sys
import glob
from collections import defaultdict

from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.common.exceptions import ELFError


def elf_files(root):
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            try:
                with open(p, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        yield p
            except OSError:
                pass


def read_elf(path):
    """-> (is64, needed[], undefined{sym}, exported{sym}) atau None"""
    try:
        with open(path, "rb") as fh:
            e = ELFFile(fh)
            is64 = e.elfclass == 64
            needed, undef, export = [], set(), set()
            for sec in e.iter_sections():
                if isinstance(sec, DynamicSection):
                    for t in sec.iter_tags():
                        if t.entry.d_tag == "DT_NEEDED":
                            needed.append(t.needed)
            dynsym = e.get_section_by_name(".dynsym")
            if dynsym is not None:
                for s in dynsym.iter_symbols():
                    if not s.name:
                        continue
                    bind = s["st_info"]["bind"]
                    if s["st_shndx"] == "SHN_UNDEF":
                        if bind != "STB_WEAK":
                            undef.add(s.name)
                    elif bind in ("STB_GLOBAL", "STB_WEAK", "STB_GNU_UNIQUE"):
                        export.add(s.name)
            return is64, needed, undef, export
    except (ELFError, OSError, ValueError, KeyError, AssertionError):
        return None


def index_libs(roots):
    """{(is64, nama.so): simbol_ekspor}"""
    idx = {}
    for r in roots:
        if not os.path.isdir(r):
            continue
        for p in elf_files(r):
            if not p.endswith(".so"):
                continue
            info = read_elf(p)
            if not info:
                continue
            key = (info[0], os.path.basename(p))
            idx.setdefault(key, set()).update(info[3])
    return idx


def manifests(root):
    return glob.glob(os.path.join(root, "etc/vintf/manifest*.xml")) + \
        glob.glob(os.path.join(root, "etc/vintf/manifest/*.xml"))


def prop(root, name):
    for f in ("build.prop", "etc/build.prop"):
        p = os.path.join(root, f)
        if os.path.isfile(p):
            for line in open(p, errors="replace"):
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
    return None


def bagian_info(vendor, odm, system, out):
    out.append("## 0. Identitas\n")
    for label, root, keys in (("vendor", vendor, ["ro.vendor.build.version.release", "ro.vendor.build.version.sdk",
                                                     "ro.vendor.build.fingerprint", "ro.vndk.version",
                                                     "ro.board.api_level", "ro.board.first_api_level"]),
                              ("sistem acuan", system, ["ro.build.version.release", "ro.build.version.sdk",
                                                        "ro.system.build.fingerprint", "ro.build.display.id"])):
        for k in keys:
            v = prop(root, k)
            if v:
                out.append(f"- {label} `{k}` = `{v}`")
    out.append("")


def bagian_vintf(vendor, odm, system, out):
    out.append("## 1. VINTF (manifest vendor vs matriks sistem)\n")
    levels = set()
    hals = set()
    for root in (vendor, odm):
        for f in manifests(root):
            txt = open(f, errors="replace").read()
            m = re.search(r'<manifest[^>]*target-level="([^"]+)"', txt)
            if m:
                levels.add(m.group(1))
                out.append(f"- `{os.path.relpath(f, os.path.dirname(root))}`: target-level **{m.group(1)}**")
            for h in re.finditer(r"<hal[^>]*>\s*<name>([^<]+)</name>", txt):
                hals.add(h.group(1).strip())
    mats = glob.glob(os.path.join(system, "etc/vintf/compatibility_matrix.*.xml"))
    supported = sorted({re.sub(r".*compatibility_matrix\.(\d+)\.xml", r"\1", m) for m in mats
                        if re.match(r".*compatibility_matrix\.\d+\.xml$", m)}, key=int)
    out.append(f"- Level yang didukung sistem acuan: **{', '.join(supported) or '(tidak ditemukan)'}**")
    for lv in sorted(levels):
        if lv in supported:
            out.append(f"- target-level {lv}: ✅ didukung")
            mat = os.path.join(system, f"etc/vintf/compatibility_matrix.{lv}.xml")
            kv = re.findall(r'<kernel version="([^"]+)"', open(mat, errors="replace").read())
            out.append(f"  - versi kernel yang diterima matriks {lv}: {', '.join(sorted(set(kv))) or '-'}")
        else:
            out.append(f"- target-level {lv}: ❌ TIDAK didukung sistem ini → gagal cek VINTF → bootloop")
    out.append(f"- Jumlah HAL dideklarasikan vendor+odm: {len(hals)}\n")
    return levels, supported


def bagian_sepolicy(vendor, system, out):
    out.append("## 2. SELinux (versi kebijakan vendor vs mapping sistem)\n")
    f = os.path.join(vendor, "etc/selinux/plat_sepolicy_vers.txt")
    ver = open(f).read().strip() if os.path.isfile(f) else None
    maps = sorted(os.path.basename(m)[:-4] for m in glob.glob(os.path.join(system, "etc/selinux/mapping/*.cil"))
                  if not m.endswith(".compat.cil"))
    out.append(f"- vendor `plat_sepolicy_vers.txt`: **{ver or '(tidak ada)'}**")
    out.append(f"- mapping yang dibawa sistem acuan: {', '.join(maps) or '(tidak ditemukan)'}")
    ok = bool(ver) and ver in maps
    out.append(f"- {'✅ ada mapping' if ok else '❌ tidak ada mapping → sepolicy gagal dikompilasi → bootloop'}\n")
    return ok


def llndk_list(roots):
    names = set()
    for r in roots:
        for f in glob.glob(os.path.join(r, "**/llndk.libraries*.txt"), recursive=True):
            names |= {l.strip() for l in open(f, errors="replace") if l.strip().endswith(".so")}
    return names


def bagian_simbol(vendor, odm, sys_roots, out):
    out.append("## 3–4. Library dan simbol (vendor+odm terhadap sistem acuan)\n")
    vend_idx = index_libs([vendor, odm])
    sys_idx = index_libs(sys_roots)
    llndk = llndk_list(sys_roots)

    missing_lib = defaultdict(set)   # lib -> pemakai
    from_system = defaultdict(set)   # lib sistem -> pemakai
    unresolved = {}                  # file -> (is64, simbol)
    checked = 0
    for p in list(elf_files(vendor)) + list(elf_files(odm)):
        info = read_elf(p)
        if not info:
            continue
        is64, needed, undef, _ = info
        checked += 1
        rel = os.path.relpath(p, os.path.dirname(vendor))
        avail = set()
        for n in needed:
            if (is64, n) in vend_idx:
                avail |= vend_idx[(is64, n)]
            elif (is64, n) in sys_idx:
                avail |= sys_idx[(is64, n)]
                from_system[n].add(rel)
            else:
                missing_lib[n].add(rel)
        rest = undef - avail
        if rest:
            unresolved[rel] = (is64, rest)

    out.append(f"- File ELF vendor+odm diperiksa: **{checked}**")
    out.append(f"- Library sistem acuan terindeks: {len(sys_idx)}; daftar LLNDK sistem: {len(llndk)} library")

    out.append(f"\n### Library dibutuhkan tapi TIDAK ADA di vendor/odm maupun sistem ({len(missing_lib)})\n")
    for lib, users in sorted(missing_lib.items(), key=lambda x: (-len(x[1]), x[0]))[:100]:
        out.append(f"- `{lib}` ← {len(users)} file, mis. `{sorted(users)[0]}`")

    not_llndk = {l: u for l, u in from_system.items() if llndk and l not in llndk}
    out.append(f"\n### Library diambil dari sistem ({len(from_system)}); yang BUKAN LLNDK (diblok namespace): {len(not_llndk) if llndk else '? (daftar LLNDK tidak ditemukan)'}\n")
    for lib, users in sorted(not_llndk.items(), key=lambda x: (-len(x[1]), x[0]))[:60]:
        out.append(f"- `{lib}` ← {len(users)} file, mis. `{sorted(users)[0]}`")
    out.append("\nSemua library sistem yang dipakai vendor: " + ", ".join(f"`{l}`" for l in sorted(from_system)))

    # Simbol yang tidak ada di NEEDED langsung bisa datang dari dependensi
    # tidak langsung; anggap gagal hanya kalau tidak diekspor library mana pun.
    pool = {True: set(), False: set()}
    for (b, _), syms in list(vend_idx.items()) + list(sys_idx.items()):
        pool[b] |= syms
    hard = {}
    for f, (is64, syms) in unresolved.items():
        miss = {s for s in syms if s not in pool[is64]}
        if miss:
            hard[f] = miss
    # simbol mana yang paling sering hilang
    count = defaultdict(int)
    for syms in hard.values():
        for s in syms:
            count[s] += 1
    total = sum(len(v) for v in hard.values())
    out.append(f"\n### Simbol yang TIDAK diekspor library mana pun ({total} simbol di {len(hard)} file)\n")
    out.append("Paling sering hilang: " + ", ".join(f"`{s}`×{n}" for s, n in sorted(count.items(), key=lambda x: -x[1])[:25]) + "\n")
    for f, syms in sorted(hard.items(), key=lambda x: (-len(x[1]), x[0]))[:100]:
        out.append(f"- `{f}` ({len(syms)}): " + ", ".join(f"`{s}`" for s in sorted(syms)[:8]) + (" …" if len(syms) > 8 else ""))
    return missing_lib, not_llndk, hard


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    vendor, odm, system, report = sys.argv[1:5]
    extra = sys.argv[5:]
    sys_roots = [os.path.join(system, d) for d in ("lib", "lib64", "etc")] + extra
    out = ["# Analisis kecocokan vendor\n",
           f"- vendor: `{vendor}`", f"- odm: `{odm}`", f"- sistem acuan: `{system}` + {len(extra)} dir tambahan\n"]
    bagian_info(vendor, odm, system, out)
    levels, supported = bagian_vintf(vendor, odm, system, out)
    se_ok = bagian_sepolicy(vendor, system, out)
    missing_lib, not_llndk, hard = bagian_simbol(vendor, odm, sys_roots, out)
    vintf_ok = bool(levels) and all(l in supported for l in levels)
    out.append("\n## Kesimpulan\n")
    out.append(f"- VINTF target-level: {'✅' if vintf_ok else '❌'}")
    out.append(f"- SELinux mapping: {'✅' if se_ok else '❌'}")
    out.append(f"- Library hilang: {len(missing_lib)}")
    out.append(f"- Library sistem non-LLNDK dipakai vendor: {len(not_llndk)}")
    out.append(f"- File dengan simbol tak terpenuhi: {len(hard)}")
    out.append(f"\n**{'BISA dicoba' if vintf_ok and se_ok and not missing_lib and not hard else 'TIDAK cocok tanpa perbaikan'}**")
    open(report, "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
