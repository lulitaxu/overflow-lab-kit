/*
 * vuln1.c - INTENTIONALLY VULNERABLE lab target. Do not expose to any network.
 *
 * Classic stack buffer overflow: gets() reads a line from stdin into a
 * 256-byte stack buffer with no bounds checking of any kind. Send more
 * than the buffer holds and you overwrite saved registers and the return
 * address.
 *
 * Practice target for: fuzz.py (stdin mode), pattern.py, badchars.py.
 *
 * Build with the labs Makefile, e.g.:
 *   gcc -m64 -fno-stack-protector -no-pie -z execstack -g -O0 -o vuln1 vuln1.c
 */
#include <stdio.h>
#include <string.h>

/* Modern glibc no longer declares gets() in <stdio.h> (it can never be
 * used safely, so the prototype was removed). The symbol still exists in
 * libc for old binaries. Declared here explicitly because this target
 * exists precisely to demonstrate why gets() is dangerous. */
extern char *gets(char *s);

int main(void)
{
    char buf[256];

    printf("vuln1: send me a line\n");
    fflush(stdout);

    gets(buf); /* no length check, ever - that is the bug on display */

    printf("vuln1: you sent: %s\n", buf);
    return 0;
}
