#!/usr/bin/env python3
"""Tambah node ramoops (sama dengan kernel vendor vayu) ke DTS vayu mainline."""
import re, sys
p = sys.argv[1]
s = open(p).read()
if "ramoops@a1600000" in s:
    print("ramoops sudah ada"); sys.exit(0)
node = """
		/* Sama dengan kernel vendor (tejas101k/kernel_xiaomi_vayu sm8150.dtsi)
		 * supaya log bisa dibaca dari ROM Android setelah restart. */
		ramoops@a1600000 {
			compatible = "ramoops";
			reg = <0x0 0xa1600000 0x0 0x800000>;
			record-size = <0x80000>;
			console-size = <0x400000>;
			pmsg-size = <0x400000>;
		};
"""
m = re.search(r"\n\treserved-memory \{\n", s)
if not m:
    sys.exit("reserved-memory tidak ditemukan")
s = s[:m.end()] + node.lstrip("\n") + "\n" + s[m.end():]
open(p, "w").write(s)
print("ramoops ditambahkan")
