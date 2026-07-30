# Progyx source security assessment

**Assessment date:** 2026-07-29  
**Assessment type:** authorized, non-destructive source and configuration review  
**Standards:** OWASP ASVS 5.0.0, OWASP WSTG, OWASP Top 10 (Broken Access Control, Security Misconfiguration, Software and Data Integrity Failures), OWASP API Security Top 10, CWE, and CVSS v4.0.

## Scope, assumptions, and limitations

The authorized scope was the local working tree at `C:\Users\User\Desktop\Push-main_pepe`, including its current uncommitted changes. No application/API/WebSocket URL, deployment, test accounts, cloud account, production logs, or explicit authorized domains were supplied. No live-service testing, brute force, destructive action, or real-data access was performed.

This report therefore distinguishes source-confirmed behavior from runtime-dependent risks. It does not assert the security of TLS, reverse-proxy behavior, cloud configuration, real rate limits, or third-party integrations. The working tree already contained uncommitted manager/outreach changes; the new `manager` role is in scope and materially affects the results.

## Executive summary

The application has several sound baseline controls: server-side JWT validation and role decorators, production cookie validation (`Secure`, `HttpOnly`, `SameSite=Strict`), CSRF/origin enforcement, one-time hashed email tokens, image re-encoding, and a deliberately hardened judge container. However, the current application has material authorization failures around lesson visibility and several defects in the critical code-runner boundary.

| Status | Critical | High | Medium | Low | Informational |
|---|---:|---:|---:|---:|---:|
| Confirmed | 0 | 4 | 0 | 0 | 0 |
| Probable / runtime-dependent | 0 | 1 | 1 | 0 | 3 |

The findings below record the original assessment evidence. The remediation update is the authoritative current state.

## Remediation update — 2026-07-29

| ID | Current status | Remediation and validation |
|---|---|---|
| C-01 | Remediated in source | A centralized deny-by-default curriculum policy now gates module listings/details, lesson payloads, dashboard continuation, mutations, and public bootstrap. Managers have no learning participation; class access is limited to members, owning teachers, and admins. Focused regressions pass. |
| C-02 | Remediated in source | Learners receive aggregate grading status only; hidden case data, labels, actual output, stderr, runner errors, and private feedback are excluded from responses and persisted learner feedback. Focused regressions pass. |
| C-03 | Remediated in source | The runner streams bounded stdout/stderr, stops on output overflow, kills process groups, and performs a final per-job-UID process sweep for detached descendants. Runner security tests pass. |
| C-04 | Remediated in source; Linux runtime verification pending | Each runner request receives a never-reused numeric UID and a private `0700` workspace. Workers drop to that UID; cleanup kills any remaining process with the UID. A fresh Linux container/CI run must confirm the effective capability and UID boundary. |
| P-01 | Remediated | Next.js and affected transitive production packages were upgraded/pinned. `npm audit --omit=dev --json` reports zero vulnerabilities; typecheck and production build pass. |
| P-02 | Remediated in source; Linux runtime verification pending | The runner self-execs before binding, removes the bearer token from its environment, transfers it once through a consumed/closed pipe, and gives workers a strict allowlist environment with closed inherited FDs. |
| I-01 | Hardened | The BFF no longer fabricates `Origin` or CSRF headers from cookies; the browser API client supplies the double-submit CSRF header for unsafe same-origin requests. |
| I-02 | Hardened | Manager contacts are limited to student/teacher/parent records and use a minimal DTO. Broadcasts remain audited and have a configurable per-manager rate limit (default: three per hour). |
| I-03 | External follow-up remains | Historical credential revocation and VCS-history remediation require the credential owner and approved repository process; no credential was accessed or rotated during this source change. |

The source fixes were regression-tested. Before production deployment, rebuild the runner image from this revision on Linux and execute the runtime checks in `docs/operations/sandbox.md`; the local Docker installation returned a stale image during this assessment.

## Threat model

| Asset | Attacker / path | Existing control | Gap / recommended control |
|---|---|---|---|
| Unpublished and classroom lesson content | Authenticated student or manager requests predictable lesson/module IDs | JWT authentication; some classroom checks | Apply one authoritative lesson-visibility policy to every list/detail/mutation endpoint. |
| Hidden grading tests and assessment integrity | Enrolled learner submits code and reads the returned judge report | Private task validation is omitted from lesson serialization | Return a learner-safe judge result only; never return test input/expected output. |
| Other learners' submitted code and grades | Learner code enumerates concurrently running same-UID runner workspaces | Read-only runner rootfs, no capabilities, resource limits | One UID/filesystem namespace/container or microVM per execution. |
| Judge service availability | Learner emits excessive output or leaves descendants | Global semaphore and container CPU/memory/PID limits | Stream with output byte caps, kill process groups, and apply per-user quotas. |
| Platform routes and server components | Remote attacker targets known Next.js advisory conditions | Backend still enforces JWT/RBAC/object checks | Patch Next.js and retest direct API plus route/proxy behavior. |

## Technical findings

### C-01 Lesson visibility and classroom authorization bypass

**Severity:** High  
**CVSS v4.0 score and vector:** 7.1 (High), `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N`  
**Confidence:** Confirmed  
**Status:** Confirmed  
**Affected component:** Learning API and new manager-role change  
**Affected endpoint or feature:** `GET /api/modules`, `GET /api/modules/<id>/lessons`, and `GET /api/lessons/<id>`  
**Affected roles:** Any authenticated user for unpublished lessons in a published module; all non-student roles for unpublished global modules; manager/parent and other non-owner roles for custom classroom lessons  
**CWE:** CWE-862, CWE-639  
**OWASP Top 10:2025:** A01 Broken Access Control  
**OWASP ASVS 5.0.0:** V8 Authorization  
**OWASP WSTG:** WSTG-ATHZ-04

#### Description

Lesson publication and ownership are not consistently enforced. `list_modules()` serializes every lesson belonging to a published module without checking `lesson.is_published`. `_user_can_access_lesson()` grants all lessons when the parent module is published, grants every non-student access to an unpublished global module, and defaults to `True` for non-student/non-teacher users of custom classroom modules. The module-detail endpoint performs no access check at all. The uncommitted manager-role change adds `MANAGER` to `LESSON_PARTICIPANT_ROLES`, making the fallback reachable through full lesson, task, and quiz endpoints.

#### Security impact

An ordinary authenticated account can read unpublished lesson summaries and, where their parent module is published, full unpublished lesson content. A manager, parent, or unrelated staff account can access another teacher's unpublished classroom lesson content. This exposes curriculum and drafts and weakens class isolation.

#### Preconditions

An authenticated account and an existing unpublished/global/custom lesson. Module and lesson IDs are returned by normal API responses, so no high-volume enumeration is necessary.

#### Reproduction steps

1. Create a published module containing an unpublished lesson, or an unpublished custom classroom module with a lesson.
2. Authenticate as a user who is not entitled to that lesson (a different student for the published-module case; manager or parent for the classroom case).
3. Request the module list/detail, then request the returned lesson ID.
4. Observe lesson summary/content rather than a 403/404.

#### Evidence

- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:675) iterates all lessons of a published module.
- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:704) loads any module ID and serializes all lessons without authorization.
- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:417) returns `True` before evaluating `lesson.is_published` and has permissive fallbacks.
- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:749) relies on that predicate for full lesson delivery.
- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:83) adds the manager role to learning participation.

#### Root cause

Publication, class membership, teacher ownership, and staff preview are implemented as scattered role branches instead of a deny-by-default, resource-aware authorization policy.

#### Remediation

Create a single server-side `can_view_lesson(user, lesson)` policy that checks both module and lesson publication, classroom membership/ownership, and an explicit admin-preview allowlist. Apply it before serializing every lesson and module. Remove manager from learner endpoints unless product requirements explicitly grant course access.

#### Secure implementation example

```python
def can_view_lesson(user: User, lesson: Lesson) -> bool:
    module = lesson.module
    if user.role in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        return True
    if module.custom_classroom_id:
        if user.role == UserRole.TEACHER:
            return Classroom.query.filter_by(
                id=module.custom_classroom_id, teacher_id=user.id
            ).first() is not None
        return (
            user.role == UserRole.STUDENT
            and ClassMembership.query.filter_by(
                classroom_id=module.custom_classroom_id, student_id=user.id
            ).first() is not None
            and lesson.is_published
        )
    return module.is_published and lesson.is_published
```

#### Regression test

Test published-module/unpublished-lesson, unpublished-global-module, and custom-classroom cases for every role. Assert both module list/detail and lesson-detail requests return no unauthorized lesson metadata or content. Test a manager explicitly receives 403/404 for learning APIs unless a policy grants it.

#### References

[OWASP WSTG-ATHZ-04](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References), [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS).

### C-02 Private code-grading tests are returned to learners

**Severity:** High  
**CVSS v4.0 score and vector:** 7.1 (High), `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:H/VA:N/SC:N/SI:N/SA:N`  
**Confidence:** Confirmed  
**Status:** Confirmed  
**Affected component:** Code grading and lesson progress  
**Affected endpoint or feature:** `POST /api/tasks/<task_id>/submit`  
**Affected roles:** Authorized lesson participant  
**CWE:** CWE-200, CWE-840  
**OWASP Top 10:2025:** A01 Broken Access Control  
**OWASP ASVS 5.0.0:** V8 Authorization; V11 Business Logic  
**OWASP WSTG:** WSTG-BUSL-03

#### Description

The task model correctly removes private validation data from lesson payloads, but the runner creates a result for every test that contains its input and expected output. The task-submit endpoint returns that complete `judge_report` unchanged to the learner.

#### Security impact

A learner can obtain the full hidden test corpus after one submission, making it possible to tailor or hard-code a solution and undermining assessment integrity.

#### Preconditions

Access to an auto-graded task.

#### Reproduction steps

1. Authenticate as an enrolled learner.
2. Submit a harmless non-passing answer to an auto-graded task.
3. Inspect `judge_report.results`; it contains `input` and `expected` for each test.

#### Evidence

- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:171) and [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:216) include test input/expected output in results.
- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:313) returns all results.
- [student.py](C:\Users\User\Desktop\Push-main_pepe\backend\app\api\student.py:986) returns the runner report directly.

#### Root cause

Internal grader diagnostics and learner-facing feedback share the same response schema.

#### Remediation

Keep full reports server-side for authorized instructors/audit only. Return the learner a DTO containing pass/fail, score, count, and a generic diagnostic with no hidden test input, expected output, or internal stack trace.

#### Secure implementation example

```python
def learner_judge_report(report: dict) -> dict:
    return {
        "passed": bool(report["passed"]),
        "score": int(report["score"]),
        "tests_passed": int(report["tests_passed"]),
        "tests_total": int(report["tests_total"]),
        "feedback": str(report["feedback"]),
    }
```

#### Regression test

Submit a failing code task and assert its response JSON contains none of `expected`, `input`, hidden labels, or internal stderr; assert the internal instructor/audit result remains available only through an authorized path.

#### References

[OWASP API Security Top 10](https://owasp.org/www-project-api-security/), [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS).

### C-03 Judge runner lacks enforceable I/O and process-lifecycle limits

**Severity:** High  
**CVSS v4.0 score and vector:** 7.1 (High), `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N`  
**Confidence:** Confirmed  
**Status:** Confirmed  
**Affected component:** Judge runner  
**Affected endpoint or feature:** Internal `/execute`, reached through code-task submission  
**Affected roles:** Authorized code-task participant  
**CWE:** CWE-400  
**OWASP Top 10:2025:** A10 Mishandling of Exceptional Conditions  
**OWASP ASVS 5.0.0:** V14 Configuration; V11 Business Logic  
**OWASP WSTG:** WSTG-BUSL-07

#### Description

The runner configures a maximum output character count, but `process.communicate()` reads all stdout and stderr into memory before the application truncates them. A submission can therefore consume the runner's 512 MiB container memory or cause a restart before the presentation cap applies. Separately, on timeout the runner kills only the direct interpreter PID. Ordinary child creation is deliberately permitted, so a descendant can survive the timeout and retain stdout/stderr file descriptors; the following `await process.communicate()` can then wait indefinitely.

#### Security impact

One authorized code learner can make code grading unavailable for other learners through memory exhaustion or a stalled timeout-cleanup path. Container memory/PID/CPU limits reduce host impact but do not guarantee recovery of the grading service.

#### Preconditions

Access to any code task using the runner.

#### Reproduction steps

In a dedicated non-production runner, submit a benign program that emits a controlled, bounded stream larger than the configured output limit and a separate controlled program that starts a short-lived child then exceeds its time limit. Observe that output is buffered before the returned diagnostic is truncated and verify all descendants are terminated. Do not perform this on a shared or production runner.

#### Evidence

- [app.py](C:\Users\User\Desktop\Push-main_pepe\judge_runner\app.py:145) passes `max_output_chars` to the engine.
- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:156) captures complete pipes using `communicate()`.
- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:201) truncates only after the capture.
- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:162) kills only the immediate PID, not a process group.
- [seccomp.json](C:\Users\User\Desktop\Push-main_pepe\judge_runner\seccomp.json:76) intentionally permits ordinary process creation.

#### Root cause

The output limit is a response-formatting control, not a subprocess I/O resource control; execution is neither started nor stopped as a dedicated process group.

#### Remediation

Read pipes incrementally with a strict byte limit; start every execution in its own process group; on timeout or output-limit breach, terminate the entire group and reap it before returning. Retain container memory/PID limits as defense in depth and add per-user submission quotas.

#### Secure implementation example

Use asynchronous stream readers that stop at a byte counter and coordinate a process-group termination; do not use an unbounded `communicate()` result as the enforcement mechanism.

#### Regression test

Run a bounded test program which exceeds the configured output limit and a harmless short-lived-child timeout test. Assert: response is prompt, output is capped, every descendant is gone, and runner RSS remains below an agreed test threshold.

#### References

[CWE-400](https://cwe.mitre.org/data/definitions/400.html), [OWASP API Security Top 10](https://owasp.org/www-project-api-security/).

### C-04 Concurrent judge executions share one UID and workspace namespace

**Severity:** High  
**CVSS v4.0 score and vector:** 7.6 (High), `CVSS:4.0/AV:N/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N`  
**Confidence:** Confirmed  
**Status:** Confirmed  
**Affected component:** Judge runner  
**Affected endpoint or feature:** Concurrent code submissions  
**Affected roles:** Concurrent authorized code-task participants  
**CWE:** CWE-668, CWE-284  
**OWASP Top 10:2025:** A01 Broken Access Control  
**OWASP ASVS 5.0.0:** V8 Authorization; V14 Configuration  
**OWASP WSTG:** WSTG-ATHZ-02

#### Description

Each judge job uses a unique temporary path, but all jobs execute concurrently as the same `judgeuser` UID. On Linux, temporary-directory permissions do not protect one process from another process with the same owner. Submitted code can list `/tmp/judge-*`, read another job's `main.py`, or modify writable files while another job runs.

#### Security impact

A learner may disclose another learner's submitted source code or interfere with grading during overlapping executions. This is a cross-user isolation failure, not a container escape.

#### Preconditions

Two overlapping runner executions and access to a code task.

#### Reproduction steps

In an isolated staging runner, start two controlled submissions concurrently. From one, verify it cannot enumerate, read, or modify the other's work directory. The current same-UID design does not provide that guarantee; do not test against real learner submissions.

#### Evidence

- [Dockerfile](C:\Users\User\Desktop\Push-main_pepe\judge_runner\Dockerfile:55) runs the runner as UID 1001.
- [app.py](C:\Users\User\Desktop\Push-main_pepe\judge_runner\app.py:30) permits concurrent execution.
- [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:264) creates workspaces under shared `/tmp` and [engine.py](C:\Users\User\Desktop\Push-main_pepe\shared\judge\engine.py:266) writes source there.

#### Root cause

Temporary path separation was used in place of principal and filesystem-namespace isolation.

#### Remediation

Run every submission in a dedicated ephemeral container/microVM with a unique UID and mounted private workspace. If an interim design is needed, allocate isolated UIDs/user namespaces, make supplied source read-only, and prevent cross-job `/proc` and `/tmp` visibility.

#### Secure implementation example

Use a controller process to create one short-lived sandbox per submission with a dedicated UID, read-only runtime, private writable work directory, no network egress, and no host/container-runtime socket.

#### Regression test

Start two controlled jobs with unique markers and assert each job cannot discover, read, rename, or write the other job's directory or source file.

#### References

[CWE-668](https://cwe.mitre.org/data/definitions/668.html), [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS).

### P-01 Framework dependencies have unresolved production security advisories

**Severity:** High  
**CVSS v4.0 score and vector:** Multiple upstream advisories; no single application CVSS assigned  
**Confidence:** Probable  
**Status:** Probable  
**Affected component:** Next.js frontend and indirect production dependencies  
**Affected endpoint or feature:** App Router, Proxy route gates, and Server Components  
**Affected roles:** Anonymous and authenticated users, depending on the upstream advisory  
**CWE:** Varies by advisory  
**OWASP Top 10:2025:** A06 Vulnerable and Outdated Components  
**OWASP ASVS 5.0.0:** V14 Configuration  
**OWASP WSTG:** WSTG-CONF-02

#### Description

`frontend/package.json` pins Next.js 16.2.1. A read-only `npm audit --omit=dev --package-lock-only --json` reported three high and two moderate production dependency advisories and recommends Next.js 16.2.12. The affected framework features are relevant because this application uses App Router and `src/proxy.ts`. No live target was available to validate any individual advisory path, and backend authorization remains an important compensating control.

#### Security impact

Known framework issues may permit denial of service or weaken frontend route/proxy behavior. A frontend gate bypass alone does not bypass the backend's JWT, role, and object checks, so this is not reported as a confirmed application authorization bypass.

#### Preconditions

A deployed version retaining the affected packages and an advisory-specific reachable condition.

#### Reproduction steps

After upgrading in a staging branch, rerun the audit and test each protected route and direct backend API request with unauthenticated, wrong-role, and malformed-session cases.

#### Evidence

- [package.json](C:\Users\User\Desktop\Push-main_pepe\frontend\package.json:17) specifies Next.js 16.2.1.
- The audit resolved `next@16.2.1` and recommended 16.2.12; advisory IDs include `GHSA-q4gf-8mx6-v5v3`, `GHSA-8h8q-6873-q5fj`, and `GHSA-26hh-7cqf-hhc6`.

#### Root cause

The project is behind currently patched production dependency versions.

#### Remediation

Upgrade Next.js to 16.2.12 or later compatible patched release, regenerate the lockfile deliberately, review release notes, rerun audit/typecheck/build, and add a scheduled dependency-review process.

#### Secure implementation example

Use a deliberate dependency update and lockfile review in a branch; do not use floating runtime package versions for production builds.

#### Regression test

Require a zero-high production audit result (with reviewed exceptions) in CI and test direct API authorization independently from frontend proxy decisions.

#### References

[GHSA-q4gf-8mx6-v5v3](https://github.com/advisories/GHSA-q4gf-8mx6-v5v3), [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS).

## Unconfirmed but material risks

| ID | Risk | Evidence and limitation | Recommended next step |
|---|---|---|---|
| P-02 | Runner token may be readable from the same-UID parent process environment via `/proc` | The token is resident in runner environment ([app.py](C:\Users\User\Desktop\Push-main_pepe\judge_runner\app.py:34)); untrusted code shares UID 1001. Actual `/proc` masking is host-dependent. | Verify `cat /proc/1/environ` is denied in a staging runner; isolate job UID and redesign runner authentication. |
| I-01 | BFF proxy fabricates CSRF header/origin values | [route.ts](C:\Users\User\Desktop\Push-main_pepe\frontend\src\app\api\[...path]\route.ts:68) derives them from cookies. Production Strict, host-only cookies and browser Origin behavior prevent a practical normal-browser exploit in the reviewed path. | Preserve strict cookie settings and add off-site/same-site-sibling BFF CSRF integration tests. |
| I-02 | Manager contact and broadcast authority needs a product-policy decision | Manager can search platform contacts and broadcast to broad audiences. It may be intentional, but policy/data-minimization evidence was not supplied. | Define role data scope, recipient caps, approval, throttling, and audit-alert requirements. |
| I-03 | Historical GigaChat credential remediation remains open | [security-followups.md](C:\Users\User\Desktop\Push-main_pepe\docs\operations\security-followups.md:6) documents the need to revoke an historical integration key and remove it from Git history. Its external status was not tested and no secret was accessed. | Revoke and replace the credential, remove historical exposure through the approved VCS process, then record evidence of completion. |

## Authorization matrix

| Resource/action | Anonymous | Student | Teacher | Parent | Manager | Admin / Superadmin | Expected authorization | Observed result |
|---|---|---|---|---|---|---|---|---|
| Published lesson | Deny | Enrolled / catalog | As product policy | As product policy | Deny | Allow preview | Explicit policy | Mostly available; not the issue tested |
| Unpublished lesson in a published module | Deny | Deny | Owner only | Deny | Deny | Preview only | Lesson-level publication check | **Fail:** any authenticated user can obtain it |
| Custom classroom lesson | Deny | Class member | Owning teacher | Deny | Deny | Preview only | Membership/ownership | **Fail:** manager/parent fall through to allow |
| Module lesson summaries | Deny | Visible only | Owner/catalog | Own scope | Deny | Preview only | Same policy as lesson | **Fail:** module-detail endpoint has no access check |
| Code task submission | Deny | Assigned/allowed lesson | Policy-specific | Deny unless assigned | Deny | Policy-specific | Lesson policy and server grading | **Fail:** manager becomes participant via C-01 |
| Parent-child data | Deny | Own only | Deny | Linked child | Deny | Staff policy | Link ownership | Source review indicates ownership checks; no live test |
| Admin users/managers | Deny | Deny | Deny | Deny | Deny | Superadmin | Superadmin only | Source review indicates role decorator |

## Endpoint inventory

This inventory groups the 150+ discovered endpoints by security boundary; the source decorators remain the detailed inventory.

| Method / endpoint family | Authentication / role | Data classification | Security-sensitive behavior | Test status |
|---|---|---|---|---|
| `POST /api/auth/*`, `GET /api/auth/me` | Public except `me` | Credentials, session state | Registration, login, refresh, reset, verification | Source + existing regression coverage reviewed |
| `GET /api/modules*`, `GET /api/lessons/*`, task/quiz submission | Authenticated / participants | Curriculum, progress, hidden tests | Visibility, grading, XP | **Fail: C-01, C-02** |
| `/api/teacher/classes/*`, submissions/grades | Teacher / object owner | Student records, grades, submissions | Classroom ownership, grading | Source reviewed; no live account test |
| `/api/parent/children/*` | Parent / link owner | Minor/student records | Parent-child link isolation | Source reviewed; no live account test |
| `/api/admin/*`, archives/media | Admin / superadmin | PII, audit logs, media | Privileged management and export | Source reviewed; manager-policy risk noted |
| `/api/messaging/*`, `/api/support/*` | Participant/staff | Messages, support data | Thread/ticket ownership | Source reviewed; no live account test |
| Internal `POST /execute` | Runner bearer token | Submitted code, hidden tests | Arbitrary-code sandbox | **Fail: C-03, C-04; P-02** |

## Code runner and sandbox report

### Current isolation architecture

The Flask backend sends authenticated requests to an unexposed `judge-runner` service. The runner supports Python and JavaScript, runs as non-root UID 1001, uses a read-only root filesystem with a writable `/tmp` tmpfs, drops capabilities, applies `no-new-privileges`, seccomp, memory/CPU/PID/file-descriptor limits, accepts a bounded HTTP request body, and sits on an internal Docker network without Internet egress.

### Assessment

| Area | Result | Evidence / limitation |
|---|---|---|
| Effective privilege | Partial | Non-root and capabilities dropped, but all jobs share one UID. |
| Filesystem / cross-user isolation | Fail | C-04: same-UID jobs can access shared temporary namespace. |
| Network isolation | Partial | No Internet egress, but documented lateral reach to backend network remains. |
| CPU/memory/PID controls | Partial | Container and rlimits exist; output is buffered before the limit (C-03). |
| Timeout / process containment | Fail | Direct PID kill only; descendant cleanup can stall `communicate()` (C-03). |
| Secrets | Partial | Minimal child environment, but parent runner token may be observable through same-UID `/proc` (P-02). |
| Hidden grading isolation | Fail | C-02 exposes full test input/expected values to learner. |
| Logging / monitoring | Partial | Execution metrics exist; no per-user capacity control was verified. |

Recommended architecture: execute each submission in a short-lived, networkless sandbox with a unique UID and private filesystem; stream capped I/O; kill a dedicated process group; do not put the controller's bearer secret in a process readable by the sandbox; and use a queue/pull model or a narrowly scoped runner credential.

## Coverage matrix

| Standard/category | Component | Test performed | Result | Evidence | Related finding | Limitation |
|---|---|---|---|---|---|---|
| ASVS V8 / WSTG authorization | Learning API | Trace list/detail/submission access predicates | Fail | `student.py` | C-01 | No live account matrix |
| API object authorization | Lesson/module resources | Compare resource lookup with policy check | Fail | `student.py:704`, `:749` | C-01 | No HTTP capture from deployed service |
| Assessment integrity | Code grading | Trace private test storage to learner response | Fail | `engine.py`, `student.py` | C-02 | No real course data used |
| Runner resource control | Subprocess I/O and timeout cleanup | Trace output-limit order and kill target | Fail | `engine.py:156`, `:162`, `:201` | C-03 | No disruptive load test |
| Runner cross-user isolation | UID/workspace design | Trace UID + concurrent temp paths | Fail | Dockerfile, engine | C-04 | Needs Linux runtime confirmation |
| Authentication/session | Flask security core | Review cookie/JWT/token logic and tests | Partial | `security.py`, security tests | — | No browser/deployment testing |
| CSRF | Backend and BFF | Review Strict cookies, origin, proxy behavior | Partial | `__init__.py`, proxy route | I-01 | No browser integration test |
| XSS / client storage | React frontend | Search dangerous sinks and browser storage | Pass for reviewed paths | React text rendering, fixed JSON-LD | — | No live DOM fuzzing |
| Uploads | Assignment media | Review byte/pixel/type validation and re-encode | Pass for reviewed path | `assignment_images.py` | — | No image-library exploit test |
| Dependency hygiene | Frontend lockfile | `npm audit` and dependency resolution | Partial | P-01 | P-01 | Advisory-specific exploit paths not live-tested |
| WebSockets / GraphQL | Repository | Route/source discovery | Not Applicable | No implementation found | — | Runtime discovery unavailable |

## Remediation roadmap

### Immediate: 0–7 days

| Item | Owner | Priority | Complexity | Dependencies | Validation |
|---|---|---|---|---|---|
| Centralize lesson/module/class authorization and remove manager learning participation | Backend platform | P0 | Medium | Product role policy | Full role-by-role API regression suite |
| Sanitize learner judge responses and rotate/remove exposed result records if retained | Learning systems + backend | P0 | Small | Teacher feedback requirements | Assert hidden test values never leave learner API |
| Stream-cap runner output and kill process groups | Backend platform | P0 | Medium | Linux runner test environment | Bounded-output and child-cleanup tests |
| Isolate each runner job by UID/container/microVM | Platform / infrastructure | P0 | High | Deployment architecture | Cross-job read/write denial test |
| Upgrade Next.js to 16.2.12+ and rerun audit | Frontend product | P0 | Small | Compatibility review | Audit, typecheck, build, protected-route tests |

### Short term: 1–4 weeks

| Item | Owner | Priority | Complexity | Dependencies | Validation |
|---|---|---|---|---|---|
| Add runner per-user throttling/quotas and capacity telemetry | Backend platform | P1 | Medium | Redis/runtime metrics | One learner cannot monopolize slots |
| Resolve runner `/proc` secret exposure by isolation/redesign | Platform | P1 | Medium | Sandbox architecture | Submitted job cannot read controller environment |
| Define manager PII/broadcast policy, caps, approvals, and alerts | Product + security | P1 | Medium | Legal/privacy policy | RBAC and abuse-control tests |
| Pin production images and dependency versions; add root `.dockerignore` | Platform | P1 | Small | Release process | Build context and image digest review |

### Medium term: 1–3 months

| Item | Owner | Priority | Complexity | Dependencies | Validation |
|---|---|---|---|---|---|
| Deploy a dedicated code-execution platform or microVM sandbox | Platform | P2 | High | Budget/operations | Independent sandbox penetration retest |
| Add DAST/API authorization tests with role fixtures | QA/security | P2 | Medium | Staging accounts | CI role matrix and negative cases |
| Centralize policy enforcement and produce API authorization inventory automatically | Backend platform | P2 | Medium | Architecture decision | Coverage report prevents unguarded routes |

## Retest plan

1. Use staging accounts for every role, two separate classes, an unpublished global module, a published module with an unpublished lesson, and a code task with hidden tests.
2. Retest C-01 through list, module-detail, lesson-detail, task, quiz, and progress endpoints. Expected result: unauthorized roles receive 403/404 and no summary leakage.
3. Retest C-02 using a deliberately failing solution. Expected result: only learner-safe status/count fields are returned; hidden input/expected data remains absent from responses, logs, and browser state.
4. Retest C-03 with bounded synthetic output and a harmless short-lived child. Expected result: output cap is enforced while streaming, all descendants are gone, and the runner remains healthy.
5. Retest C-04 with two controlled concurrent jobs. Expected result: neither can enumerate, read, or write the other's workspace.
6. Upgrade dependencies and rerun `npm audit --omit=dev --package-lock-only --json`, `npm run typecheck`, production build, and direct-backend negative authorization tests.

## Verification performed

- Read-only source/configuration review across frontend, Flask API, models, Docker Compose, runner, CI, and tests.
- `python -m unittest backend.tests.test_code_judge_security -v` — 10 tests passed.
- `python -m unittest backend.tests.test_security -v` — 17 tests passed.
- `npm audit --omit=dev --package-lock-only --json` — found five production dependency advisories; no lockfile change was made by the review.
- `npm run typecheck` — passed after dependencies were available.
- `docker compose config --quiet` — passed.
- No external systems, real credentials, real user data, or live exploitation were used.

## Prioritized development checklist

1. [ ] Fix C-01 and add complete role/class/publication negative tests before merging the manager feature.
2. [ ] Stop returning hidden judge tests immediately.
3. [ ] Fix output buffering and process-group cleanup in the runner.
4. [ ] Isolate every runner execution from every other execution.
5. [ ] Upgrade Next.js and resolve the production audit findings.
6. [ ] Decide and enforce the manager PII/broadcast scope.
7. [ ] Retest the findings in staging and commission a focused runner assessment before production use.
