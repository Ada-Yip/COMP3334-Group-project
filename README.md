# E2EE Message App

## 1) Project (E2EE message app)

This project is a **command-line secure messaging app** with a Python client and a FastAPI server.

- **Server:** manages user accounts, login sessions, friendships, blocking rules, OTP setup/verification, and encrypted message storage.
- **Client:** handles user interaction and performs end-to-end encryption/decryption before messages are sent or displayed.

Core entry points:

- Server: `main.py`
- Client: `client/app.py`

---

## 2) User feature and encryption level simple explain

### User features

- Register/login/logout
- Add friends (send/accept/decline friend requests)
- Remove friends
- Block/unblock users
- Send and read messages
- Optional message expiry (TTL)
- OTP setup and OTP login verification
- Verification-code flow for contact identity checks
- Local "verified contact" marking for trusted friends

### Encryption level (simple)

- **Key exchange:** per-user X25519 key pairs and ECDH shared key derivation
- **Message encryption:** AES-GCM (authenticated encryption)
- **Integrity + context binding:** sender/receiver/counter/TTL/timestamp are bound as AEAD associated data
- **Replay-awareness:** counters are tracked per peer
- **Key-change warning:** if a contact's public key changes, client warns before sending

> Note: this is an educational/project implementation. Treat it as a learning system unless it has completed a full professional security audit.

---

## 3) Installation steps (Python 3.12)

### Prerequisites

- Python **3.12**
- `pip`

### Install dependencies

From project root (`code/`):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional (recommended for test scripts that use `requests`):

```bash
pip install requests
```

---

## 4) Quick start for client/server

Open **two terminals** in project root (`code/`).

### Terminal 1: Start server

```bash
python main.py
```

Server default address is `http://127.0.0.1:8000` (from `config.py`).

### Terminal 2: Start client

```bash
python client/app.py
```

Then follow the CLI prompts to register/login and start messaging.

---

## 5) Test script user guide

The repository includes security/load simulation scripts:

- `load_test.py` - high-volume request load test
- `ddos_sim.py` - DDoS-like burst simulation with rotating fake IP headers
- `mitm_test.py` - key-substitution (MITM-style) simulation
- `spam_test.py` - combined runner for load + DDoS simulations

> Safety note: run these only against local/dev environments.

### A) Load test

```bash
python load_test.py --dry-run
python load_test.py --total 200 --concurrency 10
```

Useful options:

- `--base-url http://127.0.0.1:8000`
- `--endpoint /login`
- `--timeout 3`

### B) DDoS simulation

```bash
python ddos_sim.py --dry-run
python ddos_sim.py --rate 200 --duration 5 --concurrency 50 --ip-pool 200
```

### C) MITM simulation

```bash
python mitm_test.py --dry-run
python mitm_test.py
python mitm_test.py --accept-changed-key
```

- Default behavior: reject changed key and expect block/detection.
- `--accept-changed-key`: simulates risky user behavior by accepting changed key.

### D) Combined spam/security runner

```bash
python spam_test.py --dry-run
python spam_test.py
```

### Common troubleshooting

- If a script reports missing `requests`, install it:

```bash
pip install requests
```

- If you see import errors mentioning `scripts.security_*`, run scripts from project root and verify local module paths in those test files.

