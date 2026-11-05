# Overflow Lab Kit - lab target builds.
#
# These binaries are DELIBERATELY unsafe (that is their only job).
# Build and run them only inside your own lab: VM, container, or
# throwaway machine. Never expose them to a network you do not own.
#
# Flags, and why:
#   -fno-stack-protector   no stack canary, so the overflow reaches the
#                          saved return address instead of aborting early
#   -no-pie                fixed load addresses, so offsets are stable
#                          from run to run while learning
#   -z execstack           marks the stack executable (classic lab setup;
#                          v1 of this kit never puts code on the stack,
#                          it is here so the lab matches the textbooks)
#   -g -O0                 debug symbols, no optimisation surprises

CC       = gcc
CFLAGS   = -fno-stack-protector -no-pie -z execstack -g -O0 -Wall

BINS     = vuln1 vuln2 vuln3
BINS32   = vuln1_32 vuln2_32 vuln3_32

all: $(BINS) maybe32

# Native (64-bit on x86_64) targets.
vuln1 vuln2 vuln3: %: %.c
	$(CC) -m64 $(CFLAGS) -o $@ $<

# 32-bit variants (built only when multilib is installed; see maybe32).
vuln1_32 vuln2_32 vuln3_32: %_32: %.c
	$(CC) -m32 $(CFLAGS) -o $@ $<

# Probe for 32-bit support: if a trivial -m32 compile+link fails, this
# machine has no multilib and we skip the 32-bit targets with a note
# instead of failing the whole build.
maybe32:
	@if printf 'int main(void){return 0;}' | $(CC) -m32 -x c - -o /tmp/.olk_m32probe 2>/dev/null; then \
		echo "32-bit multilib found: building $(BINS32)"; \
		$(MAKE) --no-print-directory $(BINS32); \
	else \
		echo "note: -m32 not supported on this machine (no multilib), skipping 32-bit targets"; \
	fi

clean:
	rm -f $(BINS) $(BINS32)

.PHONY: all maybe32 clean
