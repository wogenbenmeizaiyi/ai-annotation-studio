from app.core.security import ensure_signing_keys


if __name__ == "__main__":
    ensure_signing_keys()
    print("Authentication signing keys are ready.")
