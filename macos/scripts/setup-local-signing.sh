#!/usr/bin/env bash
# One-time login-keychain identity. Daily build.sh signs with it, so the
# designated requirement stays the same across rebuilds and TCC keeps
# Microphone and Accessibility. The private key never leaves the keychain.
set -euo pipefail

IDENTITY="${VTT2_LOCAL_SIGN_IDENTITY:-vtt-local-codesign}"
KEYCHAIN="${HOME}/Library/Keychains/login.keychain-db"

if [[ ! -f "$KEYCHAIN" ]]; then
  echo "Login keychain not found." >&2
  exit 1
fi

if security find-identity -v -p codesigning | grep -F "\"${IDENTITY}\"" >/dev/null; then
  echo "Identity already present: ${IDENTITY}"
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! security find-certificate -c "$IDENTITY" "$KEYCHAIN" >/dev/null 2>&1; then
  cat > "$TMP/cert.conf" << EOF
[ req ]
distinguished_name = dn
x509_extensions = ext
prompt = no
[ dn ]
CN = ${IDENTITY}
[ ext ]
basicConstraints = critical, CA:TRUE
keyUsage = critical, digitalSignature, keyCertSign
extendedKeyUsage = critical, codeSigning
subjectKeyIdentifier = hash
EOF

  openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
    -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
    -config "$TMP/cert.conf" >/dev/null 2>&1

  P12_PASS="$(openssl rand -hex 16)"
  # The login keychain imports only the older PKCS#12 algorithms (3DES, SHA-1 MAC).
  # Name them explicitly: OpenSSL 3 defaults to AES, and macOS /usr/bin/openssl
  # (LibreSSL) has no -legacy flag. These flags work with both.
  openssl pkcs12 -export \
    -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg sha1 \
    -inkey "$TMP/key.pem" -in "$TMP/cert.pem" \
    -out "$TMP/cert.p12" -passout "pass:${P12_PASS}"

  security import "$TMP/cert.p12" -k "$KEYCHAIN" -P "$P12_PASS" -f pkcs12 -A >/dev/null
fi

security find-certificate -c "$IDENTITY" -p "$KEYCHAIN" > "$TMP/cert.pem"
security add-trusted-cert -r trustRoot -p codeSign -k "$KEYCHAIN" "$TMP/cert.pem"

if ! security find-identity -v -p codesigning | grep -F "\"${IDENTITY}\"" >/dev/null; then
  echo "Certificate is in the login keychain but is not a codesigning identity yet." >&2
  echo "Keychain Access → login → ${IDENTITY} → Trust → Always Trust, then re-run this script." >&2
  exit 1
fi

echo "Code signing identity ready: ${IDENTITY}"
echo "The next VoiceToText rebuild still needs one permission grant. Later rebuilds keep it."
