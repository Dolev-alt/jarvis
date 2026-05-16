import json
import os
import base64
import hashlib
import subprocess

_VAULT_FILE = os.path.join(os.path.dirname(__file__), "..", "vault.enc")
_VAULT_HASH_FILE = os.path.join(os.path.dirname(__file__), "..", "vault.hash")


def _derive_key(password):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"JARVIS_VAULT_SALT_2026", 100000)


def _simple_encrypt(data, key):
    """XOR-based encryption (use cryptography lib if available for AES)."""
    try:
        from cryptography.fernet import Fernet
        fernet_key = base64.urlsafe_b64encode(key[:32])
        f = Fernet(fernet_key)
        return f.encrypt(json.dumps(data).encode()).decode()
    except ImportError:
        pass

    raw = json.dumps(data).encode()
    encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw)])
    return base64.b64encode(encrypted).decode()


def _simple_decrypt(encrypted_str, key):
    try:
        from cryptography.fernet import Fernet
        fernet_key = base64.urlsafe_b64encode(key[:32])
        f = Fernet(fernet_key)
        return json.loads(f.decrypt(encrypted_str.encode()).decode())
    except ImportError:
        pass
    except Exception:
        return None

    try:
        raw = base64.b64decode(encrypted_str)
        decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw)])
        return json.loads(decrypted.decode())
    except Exception:
        return None


def _verify_master(password):
    if not os.path.exists(_VAULT_HASH_FILE):
        return True
    with open(_VAULT_HASH_FILE, "r") as f:
        stored = f.read().strip()
    return hashlib.sha256(password.encode()).hexdigest() == stored


def _set_master(password):
    with open(_VAULT_HASH_FILE, "w") as f:
        f.write(hashlib.sha256(password.encode()).hexdigest())


def _load_vault(password):
    if not os.path.exists(_VAULT_FILE):
        return {}
    key = _derive_key(password)
    with open(_VAULT_FILE, "r") as f:
        encrypted = f.read().strip()
    data = _simple_decrypt(encrypted, key)
    return data if isinstance(data, dict) else {}


def _save_vault(data, password):
    key = _derive_key(password)
    encrypted = _simple_encrypt(data, key)
    with open(_VAULT_FILE, "w") as f:
        f.write(encrypted)


def execute(params):
    action = params.get("action", "get").lower()
    master = params.get("master_password", "").strip()

    if not master:
        master = os.getenv("JARVIS_VAULT_MASTER", "")
    if not master:
        return "Master password required. Set JARVIS_VAULT_MASTER in .env or provide master_password param."

    if action == "init":
        if os.path.exists(_VAULT_HASH_FILE):
            return "Vault already initialized."
        _set_master(master)
        _save_vault({}, master)
        return "Secure vault initialized with master password."

    if not _verify_master(master):
        return "Invalid master password."

    if action == "save":
        key = params.get("key", "").strip()
        value = params.get("value", "").strip()
        if not key or not value:
            return "Both key and value required. Example: key='gmail', value='my_password'"
        vault = _load_vault(master)
        vault[key] = {
            "value": value,
            "updated": __import__("time").strftime("%Y-%m-%d %H:%M"),
        }
        _save_vault(vault, master)
        return f"Secret '{key}' saved securely."

    if action == "get":
        key = params.get("key", "").strip()
        if not key:
            return "No key specified."
        vault = _load_vault(master)
        entry = vault.get(key)
        if entry:
            val = entry['value']
            masked = val[:2] + "*" * max(0, len(val) - 4) + val[-2:] if len(val) > 4 else "****"
            try:
                subprocess.run(["pbcopy"], input=val.encode(), check=True, timeout=5)
                return f"Secret '{key}': {masked} (updated: {entry.get('updated', 'unknown')}). Full value copied to clipboard."
            except Exception:
                return f"Secret '{key}': {masked} (updated: {entry.get('updated', 'unknown')}). Could not copy to clipboard."
        return f"No secret found for '{key}'."

    if action == "list":
        vault = _load_vault(master)
        if not vault:
            return "Vault is empty."
        lines = [f"- {k} (updated: {v.get('updated', 'unknown')})" for k, v in vault.items()]
        return f"Vault entries ({len(vault)}):\n" + "\n".join(lines)

    if action == "delete":
        key = params.get("key", "").strip()
        vault = _load_vault(master)
        if key in vault:
            del vault[key]
            _save_vault(vault, master)
            return f"Secret '{key}' deleted."
        return f"No secret found for '{key}'."

    return f"Unknown vault action: {action}. Use: init, save, get, list, delete."
