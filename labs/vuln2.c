/*
 * vuln2.c - INTENTIONALLY VULNERABLE lab target. Do not expose to any network.
 *
 * strcpy() copies argv[1] into a 128-byte stack buffer with no length
 * check. A long enough command-line argument overwrites saved registers
 * and the return address.
 *
 * Practice target for: pattern.py (feed the pattern as the argument,
 * read the crash value), badchars.py.
 *
 * Build with the labs Makefile, e.g.:
 *   gcc -m64 -fno-stack-protector -no-pie -z execstack -g -O0 -o vuln2 vuln2.c
 */
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    char buf[128];

    if (argc < 2) {
        printf("usage: %s <string>\n", argv[0]);
        return 1;
    }

    strcpy(buf, argv[1]); /* copies until NUL, no bounds check - the bug */

    printf("vuln2: you sent: %s\n", buf);
    return 0;
}
