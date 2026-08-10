# Bundled CA certificate

`vitap_sectigo_intermediate.pem` is the **Sectigo Public Server Authentication
CA DV R36** intermediate certificate.

## Why it is here

VTOP's server (`vtop.vitap.ac.in`) is misconfigured: it presents only its leaf
certificate and omits this intermediate CA from the TLS chain. Browsers and
curl paper over this by fetching the missing intermediate automatically (the
AIA mechanism), but Python's `ssl` module does not. Without the intermediate,
verification fails with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer
certificate`.

The client loads this cert alongside the normal `certifi` roots so the chain
`leaf -> this intermediate -> Sectigo root` can be built and verified. TLS
verification stays fully enabled; nothing is bypassed.

This mirrors the `lib_vtop` rust crate, which bundles the same certificate as
`VITAP_CUSTOM_CERT_PEM` and adds it to its rustls root store.

## Provenance

- Subject: `Sectigo Public Server Authentication CA DV R36`
- Issuer: `Sectigo Public Server Authentication Root R46`
- Official source: `http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt`
  (named as the CA-issuer in VTOP's own leaf certificate)

## When to update

If VTOP renews its certificate under a different CA, TLS will start failing
again. Fetch the new intermediate named in the leaf's "CA Issuers" URL,
convert it to PEM, and replace this file:

```bash
openssl s_client -connect vtop.vitap.ac.in:443 -servername vtop.vitap.ac.in \
  2>/dev/null | openssl x509 -noout -text | grep -A1 "CA Issuers"
```
