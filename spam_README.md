# Security Test Scripts

These scripts simulate high-volume traffic against the local FastAPI server.
They are designed for local testing only.

## Safety

- Defaults target `config.SERVER_URL` (usually `http://127.0.0.1:8000`).
- For non-local targets, use `--allow-remote` explicitly.
- Use `--dry-run` to preview without sending requests.

## Quick usage

Load test (single-client burst):

```
python scripts/security_load_test.py --total 200 --concurrency 10
```

DDoS simulation (many IPs):

```
python scripts/security_ddos_sim.py --rate 200 --duration 5 --concurrency 50 --ip-pool 200
```

Runner (small defaults):

```
python scripts/security_test_runner.py
```

