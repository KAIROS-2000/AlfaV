# Judge-runner sandbox hardening (P0-4)

The judge-runner executes arbitrary user-submitted code. It is the
highest-risk component in the stack. This document describes the layered
defences that are currently in place and what operators MUST verify before
enabling the profile on a new host.

## Layers of defence (top → bottom)

1. **Container filesystem is read-only** (`read_only: true`).
   Only `/tmp` is writable and mounted as a `tmpfs` with `noexec,nosuid` and
   a small size cap (128 MiB).
2. **Minimal dispatcher capabilities.** Compose drops all capabilities, then
   restores only `CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`, and `KILL` for the
   trusted dispatcher to prepare and remove per-worker workspaces. Submitted
   workers run after `setuid` and do not retain those capabilities.
3. **No new privileges** (`security_opt: no-new-privileges:true`). setuid
   binaries cannot elevate.
4. **Custom seccomp profile** (`judge_runner/seccomp.json`, see below).
5. **Per-submission identity and workspace.** The trusted HTTP dispatcher
   allocates a never-reused numeric UID for each submission, creates its
   `/tmp/judge-*` tree with mode `0700`, and drops the Python/Node worker to
   that UID before `exec`. Concurrent workers therefore cannot read or modify
   another submission's workspace even though they share a container. The
   dispatcher is UID 0 solely for this setup/cleanup operation and retains only
   `CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`, and `KILL`; submitted workers lose those
   capabilities after `setuid`.
6. **Bounded output and process cleanup.** Stdout and stderr are consumed as
   streams into bounded buffers rather than accumulated with `communicate()`.
   The runner starts each execution in its own POSIX process group and kills
   that group on timeout, output overflow, or leader exit. Cleanup then
   SIGKILLs any remaining process with that submission's unique worker UID,
   which also catches descendants that deliberately detached with `setsid`.
7. **Process limit** (`pids_limit: 128`) caps fork-bombs at the cgroup level.
8. **Resource limits**:
   - `mem_limit: 512m`, `memswap_limit: 512m` → no swap escape from the
     memory cap.
   - `cpus: 1.0` → a single logical core per container.
   - `ulimits.nproc: 64`, `ulimits.nofile: 256/256` → per-process rlimits as
     a second line of defence behind `pids_limit`.
9. **Network isolation through a one-purpose gateway.** Production Compose
   uses two separate internal bridges. Backend connects to `judge_client_net`;
   judge-runner connects to `judge_worker_net`; only `judge-gateway` is
   dual-homed. The gateway exposes `/execute` and `/health`, is not a general
   forward proxy, and has no route for arbitrary backend requests. Submitted
   code therefore cannot resolve or connect directly to backend, PostgreSQL,
   Redis, the host, or the Internet.

   Before binding its HTTP socket, the runner self-execs with a sanitized
   environment. It passes the inbound bearer token once through an inherited
   pipe, consumes and closes that descriptor, and gives worker processes a
   strict allowlist environment with `close_fds=True`. A worker can reach the
   fixed gateway listener but cannot authenticate a recursive `/execute`
   request and cannot use it to proxy arbitrary destinations.

   CI submits adversarial Python code that attempts to connect to
   `backend:8000`; the judge result must be exactly `blocked`.
10. **Unprivileged submitted code.** Every submitted Python/Node process runs
   as its fresh numeric worker UID, not as the root dispatcher. Combined with
   `no-new-privileges` and the capability drop after `setuid`, this makes
   privilege escalation within the container materially harder.
11. **No published ports**. The service exposes 8090 only on the internal
   `judge_worker_net`.

## Seccomp profile

File: `judge_runner/seccomp.json`.

### Strategy chosen

**Allow-by-default with a curated denylist.** The profile sets
`defaultAction: SCMP_ACT_ALLOW` and explicitly blocks syscalls that are not
required to run standard Python / Node programs but which have historically
been used in container escapes or which manipulate kernel-wide state:

- Mount / filesystem: `mount`, `umount`, `umount2`, `pivot_root`, `chroot`,
  `open_by_handle_at`, `name_to_handle_at`, `sysfs`, `ustat`.
- Kernel modules / arbitrary code: `init_module`, `finit_module`,
  `delete_module`, `create_module`, `query_module`, `get_kernel_syms`,
  `kexec_load`, `kexec_file_load`, `bpf`.
- Namespace / clone: `unshare`, `setns`, restricted `clone` flags (see
  caveat below).
- Tracing / cross-VM peek: `ptrace`, `process_vm_readv`, `process_vm_writev`,
  `perf_event_open`, `kcmp`, `lookup_dcookie`.
- Time / host manipulation: `clock_settime`, `clock_adjtime`,
  `settimeofday`, `stime`, `sethostname`, `setdomainname`.
- Swap / quotas / accounting: `swapon`, `swapoff`, `quotactl`, `acct`.
- Legacy / obscure: `uselib`, `vm86`, `vm86old`, `userfaultfd`, `ioperm`,
  `iopl`, `personality`, `reboot`, `nfsservctl`.
- Keyring: `add_key`, `request_key`, `keyctl`.
- NUMA / memory policy: `mbind`, `set_mempolicy`, `get_mempolicy`,
  `migrate_pages`, `move_pages`.
- Fanotify: `fanotify_init`.

Denied syscalls return `EPERM` (errno 1) to the caller.

### Why not a strict whitelist?

A strict whitelist (default-deny, enumerate allowed syscalls) is stronger
but is fragile under Python/Node runtime upgrades — a new glibc or a new V8
version can introduce new syscalls that then fail in ways that look like
application bugs. The allow-default-deny-dangerous profile chosen here is a
pragmatic intermediate; it is materially stronger than the Docker default
(which has a larger allowlist oriented at general container workloads).

A follow-up task is to move to a strict whitelist once the runtime matrix
is stable; `judge_runner/seccomp.json` is a good base for that work.

### Caveat: `clone` / `clone3` filtering

The profile blocks `clone` only when the `CLONE_NEWUSER` flag is present.
Ordinary process creation must remain available because the runner uses
subprocesses to execute Python and Node solutions. The profile also denies
`clone3` with `ENOSYS`: seccomp cannot inspect the flags inside `clone3`'s
pointer argument, and returning `ENOSYS` lets runtimes fall back to `clone`
when they support that path.

Operators SHOULD still validate this on the target host: run the
judge-runner under seccomp, run the full judge test matrix, and confirm that
user-namespace creation remains blocked.

## Verification checklist (required before enabling on a new host)

Run these from the host after `docker compose up -d judge-runner`:

1. **Seccomp is loaded:**
   ```
   docker inspect --format='{{.HostConfig.SecurityOpt}}' proghub-judge-runner
   ```
   Must include `seccomp=...seccomp.json`.
2. **Capability budget:**
   ```
   docker inspect --format='{{.HostConfig.CapDrop}} / {{.HostConfig.CapAdd}}' proghub-judge-runner
   ```
   Expected: `[ALL] / [CHOWN SETUID SETGID DAC_OVERRIDE KILL]`; these are used
   only by the trusted dispatcher before workers drop to their per-request UID.
3. **Dispatcher capabilities and worker UID:**
   ```
   docker inspect --format='{{.HostConfig.CapDrop}} / {{.HostConfig.CapAdd}}' proghub-judge-runner
   ```
   Expected: `[ALL] / [CHOWN SETUID SETGID DAC_OVERRIDE KILL]`. Submitted programs
   must report a non-zero, per-request UID and no effective capabilities.
4. **Read-only rootfs:**
   ```
   docker exec proghub-judge-runner sh -c 'touch /abc 2>&1 || echo OK'
   ```
   Expected: `OK`.
5. **No internet egress:**
   ```
   docker exec proghub-judge-runner sh -c 'python -c "import urllib.request; urllib.request.urlopen(\"http://example.com\", timeout=2)"'
   ```
   Expected: network failure.
6. **No direct backend reachability:** submit code that resolves/connects to
   `backend:8000`; it must return a DNS or connection failure. CI contains the
   canonical regression test.
7. **Full Python and Node smoke tests pass** — run the backend's judge
   integration tests against this container. If any syscall in the denylist
   is in fact needed by the runtime, tests will fail with a clear EPERM
   error; remove the offending syscall from the denylist and document why.
8. **AppArmor (Linux hosts only):** on Debian/Ubuntu hosts, verify that the
   container is confined by the `docker-default` AppArmor profile:
   ```
   docker inspect --format='{{.AppArmorProfile}}' proghub-judge-runner
   ```
   Expected: `docker-default` (this is automatic on Linux hosts with
   AppArmor; it is a no-op on non-Linux Docker Desktop). The compose file
   does not explicitly set it to avoid breaking macOS/Windows dev
   environments.

## If you suspect the seccomp profile is breaking submissions

Temporarily revert to Docker's default by editing the `security_opt:` block
in `compose.yml` (comment out the `seccomp=...` line) and restart
the container. File an issue with the failing submission + the kernel
syscall trace (capture with `strace -f -c` attached to the runner).
