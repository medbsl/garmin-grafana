# Maintained security fork

This fork is maintained at https://github.com/medbsl/garmin-grafana for the
collector consumed by medbsl/bousselmiWebsite. Upstream remains
https://github.com/arpanghosh8453/garmin-grafana. Preserve its license and attribution.

## Reviewed update — 2026-10-17

Based on upstream 895bfa7f7bde6e4cd14380533d4650cfe865d1aa. Compared with the
parent application's former pin 8e47830364817bc1a355eab857fa0535a99d401f,
upstream corrects bulk-export activity units, tolerates missing FIT data, and
handles null activity durations. The offline suite covers bulk unit conversion.

Updated the locked msgpack, pyarrow, urllib3 and setuptools dependencies while
preserving the Garmin client and InfluxDB client versions. Replaced the old
Bookworm/uv images with a digest-pinned Python 3.13 Trixie base. The final image
contains no pip bootstrap tooling, runs as UID/GID 1000, and keeps application
code and its virtual environment root-owned. Existing token-volume ownership
and the collector command are preserved. The build uses uv 0.13.1 and the lockfile.

Fork CI builds the image and runs offline compatibility tests without network
access, provider credentials, or database writes. Upstream image publication and
Codeberg synchronization are restricted to upstream. This fork does not deploy.

## Updating

Review upstream changes and dependency changes before merging into main. Run:

```sh
docker build -t garmin-collector:test .
docker run --rm --network none -v "$PWD/tests:/tests:ro" garmin-collector:test python -m unittest discover -s /tests -v
```

Scan both the lockfile and the final image using the parent repository's pinned
security tooling. Push the tested fork commit before updating the parent's
submodule reference. The parent security workflow is authoritative for deployment
and must pass for the exact parent commit. A passing compatibility suite is not
security approval.

## Executed validation

Nine Docker offline compatibility tests and four parent dashboard token tests pass.
The locked dependency Trivy scan reports no High/Critical vulnerabilities. The
local ARM64 runtime scan reports 168 findings, 47 blocking findings and no scanner
errors; this is not an AMD64 production-image certification. The new CI workflow
passes actionlint. Hosted execution is checked separately after publication.

## Remaining limitations

The Trixie base still has scanner-reported OS vulnerabilities. These are not
waived. Kubernetes examples retain security findings and have not been tested on
a cluster. There is no fabricated HTTP health endpoint for this background
collector. Live Garmin authentication, MFA and production ingestion are not
exercised by the offline tests. No stored credentials are rotated by these changes.

## Kubernetes example hardening — 2026-10-17

The example now uses a dedicated namespace, disables Kubernetes API token
mounts, drops Linux capabilities, prevents privilege escalation, sets resource
requests/limits and RuntimeDefault seccomp, and adds service health probes.
Collector and Grafana use their existing image UIDs with matching volume groups.
Single-replica deployments use Recreate to avoid competing writers on their PVCs.
Ingress policies deny inbound collector traffic, restrict InfluxDB to the two
in-namespace clients, and preserve Grafana's HTTP NodePort access. Egress remains
available for Garmin, DNS and plugin downloads.

Checkov 3.3.29 reports 257 passed and 16 failed checks, zero skips and zero parsing
errors (previously 68 failures). Existing secrets/configuration values, PVC specs,
service ports, image references and mounts were checked for preservation. This
was static validation, not a live Kubernetes deployment. Review memory limits
against data volume and configure a NetworkPolicy-capable CNI before applying.
Moving an existing default-namespace installation requires a separate storage
migration; do not apply this as an in-place namespace migration. No production
resources or credentials were changed. Remaining findings are not exempted.
