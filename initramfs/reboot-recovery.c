// SPDX-License-Identifier: GPL-2.0
/*
 * Restart ke recovery: reboot(LINUX_REBOOT_CMD_RESTART2, "recovery").
 * Kernel menulis mode "recovery" ke PMIC (qcom,pm8998-pon mode-recovery),
 * bootloader membacanya lalu memuat partisi recovery.
 *
 * Tanpa libc (busybox reboot tidak bisa memberi argumen "recovery").
 * Build: clang --target=aarch64-linux-gnu -static -nostdlib -ffreestanding \
 *        -fno-stack-protector -O2 -o reboot-recovery reboot-recovery.c
 */

#define SYS_write	64
#define SYS_sync	81
#define SYS_reboot	142
#define SYS_exit	93

#define LINUX_REBOOT_MAGIC1	0xfee1dead
#define LINUX_REBOOT_MAGIC2	672274793
#define LINUX_REBOOT_CMD_RESTART2	0xA1B2C3D4

static long sc4(long n, long a, long b, long c, long d)
{
	register long x8 __asm__("x8") = n;
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;

	__asm__ volatile("svc #0"
			 : "+r"(x0)
			 : "r"(x8), "r"(x1), "r"(x2), "r"(x3)
			 : "memory");
	return x0;
}

void _start(void)
{
	static const char msg[] = "reboot-recovery: restart ke recovery\n";
	static const char err[] = "reboot-recovery: GAGAL\n";

	sc4(SYS_write, 2, (long)msg, sizeof(msg) - 1, 0);
	sc4(SYS_sync, 0, 0, 0, 0);
	sc4(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
	    LINUX_REBOOT_CMD_RESTART2, (long)"recovery");
	sc4(SYS_write, 2, (long)err, sizeof(err) - 1, 0);
	sc4(SYS_exit, 1, 0, 0, 0);
	for (;;)
		;
}
