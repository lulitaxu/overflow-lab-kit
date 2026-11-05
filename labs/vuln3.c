/*
 * vuln3.c - INTENTIONALLY VULNERABLE lab target. Lab use only.
 *
 * Tiny TCP server: listens on a port (argv[1], default 9999), accepts one
 * connection at a time, recv()s whatever arrives into a big staging
 * buffer, then strcpy()s it into a 256-byte stack buffer. A long message
 * overwrites saved registers and the return address and kills the
 * server. Binds on all local interfaces like a naive lab service would;
 * run it only inside your own lab (VM / container), ideally reachable
 * only from localhost.
 *
 * Practice target for: fuzz.py (tcp mode), pattern.py, badchars.py.
 *
 * Build with the labs Makefile, e.g.:
 *   gcc -m64 -fno-stack-protector -no-pie -z execstack -g -O0 -o vuln3 vuln3.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>

static void handle_client(int conn)
{
    /* The staging buffer is static (BSS), NOT a stack local, on purpose:
     * with both buffers as stack locals the compiler is free to place the
     * 4096-byte staging array between buf and the saved return address,
     * where it silently absorbs the overflow (verified during this kit's
     * build: a 400-byte message overflowed a stack-local layout, landed
     * in the staging array, and the server kept running). Keeping this
     * frame to just buf means the strcpy overflow marches straight at
     * the saved registers, which is the behaviour the lab exists to show. */
    static char data[4096];
    char buf[256];
    ssize_t n;

    n = recv(conn, data, sizeof(data) - 1, 0);
    if (n <= 0)
        return;
    data[n] = '\0';

    printf("vuln3: received %zd bytes\n", n);
    fflush(stdout);

    strcpy(buf, data); /* unbounded copy into a 256-byte stack buffer */

    printf("vuln3: copied: %s\n", buf);
    fflush(stdout);
}

int main(int argc, char **argv)
{
    int port = 9999;
    int srv, conn, one = 1;
    struct sockaddr_in addr;

    if (argc > 1)
        port = atoi(argv[1]);

    srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv < 0) {
        perror("socket");
        return 1;
    }
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((unsigned short)port);

    if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }
    if (listen(srv, 5) < 0) {
        perror("listen");
        return 1;
    }

    printf("vuln3: listening on port %d\n", port);
    fflush(stdout);

    for (;;) {
        conn = accept(srv, NULL, NULL);
        if (conn < 0) {
            perror("accept");
            continue;
        }
        handle_client(conn);
        close(conn);
    }

    return 0;
}
