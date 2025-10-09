# Linux Code Signing Options for MeerK40t

## Overview

Linux does not have a standardized code signing system like Windows (Authenticode) or macOS (codesign). However, there are several approaches available for signing Linux applications, particularly for AppImages which are the primary distribution format for MeerK40t on Linux.

## Option 1: GPG Signing of AppImages (Recommended)

**Pros:** Industry standard for Linux, provides authenticity verification, widely supported
**Cons:** Requires GPG key management, users need to verify signatures manually

AppImages can be signed with GPG keys, providing cryptographic verification of authenticity and integrity.

### Setup Process:

1. **Generate or Import GPG Key:**
   ```bash
   # Generate a new GPG key (if you don't have one)
   gpg --full-generate-key

   # Or import existing key
   gpg --import private-key.asc
   ```

2. **Export Public Key:**
   ```bash
   # Export public key for distribution
   gpg --export --armor your-email@example.com > public-key.asc
   ```

3. **Configure GitHub Secrets:**
   - `GPG_PRIVATE_KEY`: Base64 encoded private GPG key
   - `GPG_PASSPHRASE`: GPG key passphrase (if applicable)
   - `GPG_KEY_ID`: GPG key ID (email or fingerprint)

4. **Update Workflow:**
   - Uncomment the GPG signing lines in `.github/workflows/appimage.yml` and `.github/workflows/ubuntu.yml`
   - The workflow will sign the AppImage with your GPG key

### Verification by Users:
Users can verify AppImage signatures with:
```bash
# Import the public key
gpg --import public-key.asc

# Verify the AppImage signature
gpg --verify MeerK40t-x86_64.AppImage.asc MeerK40t-x86_64.AppImage
```

### Benefits:
- Cryptographic verification of AppImage authenticity
- Protection against tampering
- Industry standard for Linux software distribution
- Works with package managers and repositories

## Option 2: No Code Signing (Default)

**Pros:** Simple, no setup required
**Cons:** No authenticity verification, users cannot verify software integrity

The current workflow uses this approach by default. AppImages work without signing, but users have no way to verify the software hasn't been tampered with.

## Option 3: Checksums Only

**Pros:** Basic integrity verification, very simple
**Cons:** No authenticity verification, doesn't prevent malicious modifications

Generate SHA256 checksums for distribution:
```bash
sha256sum MeerK40t-x86_64.AppImage > MeerK40t-x86_64.AppImage.sha256
```

Users can verify with:
```bash
sha256sum -c MeerK40t-x86_64.AppImage.sha256
```

## Option 4: Flatpak/Snap Signing

**Pros:** Built-in signing for containerized applications
**Cons:** Requires converting to Flatpak/Snap format, more complex distribution

If MeerK40t were distributed as Flatpak or Snap packages, these formats have built-in signing mechanisms using the respective store keys.

## Current Workflow Behavior

- **Default:** No code signing (AppImages work but cannot be verified)
- **File names:** `meerk40t-{tag}-x86_64.AppImage` and `MeerK40t-Ubuntu-Latest.AppImage`
- **Distribution:** AppImages can be downloaded and run without signing

## For Production Distribution

For professional Linux distribution, consider:

1. **GPG signing** - Most appropriate for direct AppImage distribution
2. **Flatpak/Snap stores** - Built-in signing and distribution infrastructure
3. **Package repositories** - Distribution through official repositories with package signing
4. **Checksums** - At minimum, provide SHA256 checksums for integrity verification

The current setup works for development and testing purposes, but GPG signing is recommended for production releases to ensure users can verify software authenticity.</content>
<parameter name="filePath">c:\_development\meerk40t\LINUX_CODE_SIGNING.md
