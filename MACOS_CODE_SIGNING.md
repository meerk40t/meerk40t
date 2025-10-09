# Free macOS Code Signing Options for MeerK40t

## Option 1: No Code Signing (Simplest - Default)

**Pros:** Free, no setup required
**Cons:** App shows as "untrusted" in macOS, users need to right-click > Open

The workflow currently uses this approach by default.

## Option 2: Self-Signed Certificate (Free)

**Pros:** Free, provides basic code signing
**Cons:** Still shows warnings, not trusted by macOS

To enable:

1. Uncomment the self-signed certificate lines in the workflow
2. The workflow will create and use a self-signed certificate

## Option 3: Free Apple Developer Account (Limited)

**Pros:** Proper code signing with Apple certificate
**Cons:** Limited to development use only, cannot distribute publicly

To set up:

1. Create free Apple Developer account at developer.apple.com
2. Create a "Developer ID Application" certificate
3. Export the certificate as .p12 file
4. Add to GitHub secrets:
   - `MACOS_CERTIFICATE_P12`: Base64 encoded .p12 file
   - `MACOS_CERTIFICATE_PASSWORD`: Certificate password
   - `MACOS_CERTIFICATE_NAME`: Certificate name (e.g., "Developer ID Application: Your Name")
5. Uncomment the Apple certificate lines in the workflow

## Option 4: SSL.com Free Code Signing (Recommended for Open Source)

**Pros:** Free for open source projects, provides trusted code signing, no macOS warnings
**Cons:** Requires account setup and certificate management

SSL.com offers free code signing certificates for verified open source projects through their Open Source Code Signing program.

### Setup Process:

1. **Apply for Free Certificate:**
   - Visit https://www.ssl.com/code-signing/sslcom-free-code-signing
   - Fill out the application form for open source projects
   - Provide project details and GitHub repository link
   - Wait for approval (usually 1-2 business days)

2. **Download Certificate:**
   - Once approved, download the code signing certificate (.p12 or .pfx file)
   - Note the certificate password provided

3. **Add to GitHub Secrets:**
   - Base64 encode the certificate file:
     ```bash
     base64 -i certificate.p12
     ```
   - Add to GitHub repository secrets:
     - `MACOS_CERTIFICATE_P12`: The base64 encoded certificate
     - `MACOS_CERTIFICATE_PASSWORD`: Certificate password
     - `MACOS_CERTIFICATE_NAME`: Certificate name (usually "SSL.com Code Signing")

4. **Update Workflow:**
   - Uncomment the SSL.com certificate lines in `.github/workflows/macos.yml`
   - The workflow will use the SSL.com certificate for code signing

### Requirements:
- Project must be open source with public repository
- Must provide project details and links
- Certificate is valid for 1 year, renewable annually

### Benefits:
- Apps signed with SSL.com certificates are trusted by macOS
- No "untrusted developer" warnings
- Professional appearance for downloads
- Free for qualifying open source projects

## Option 5: SignPath.io Code Signing (Free for Open Source)

**Pros:** Free for open source projects, automated GitHub integration, trusted certificates
**Cons:** Requires GitHub integration setup, limited to certain certificate types

SignPath.io provides free code signing for open source projects through their GitHub integration.

### Setup Process:

1. **Create SignPath Account:**
   - Visit https://signpath.io
   - Sign up for a free account
   - Connect your GitHub repository

2. **Configure Signing Policy:**
   - Create a signing policy for macOS code signing
   - Choose certificate type (OV or EV, depending on free tier limits)
   - Configure GitHub Actions integration

3. **GitHub Integration:**
   - Install SignPath GitHub App in your repository
   - Add the following secrets to your GitHub repository:
     - `SIGNPATH_API_TOKEN`: Your SignPath API token
     - `SIGNPATH_ORG_ID`: Your SignPath organization ID
   - The workflow will automatically use SignPath for signing

### Example Workflow Integration:
The workflow includes a SignPath signing step that runs automatically when the secrets are configured:

```yaml
- name: Code Sign with SignPath (Optional)
  if: env.SIGNPATH_API_TOKEN != ''
  uses: signpath/github-action-submit-signing-request@v1
  with:
    api-token: '${{ secrets.SIGNPATH_API_TOKEN }}'
    organization-id: '${{ secrets.SIGNPATH_ORG_ID }}'
    project-slug: 'meerk40t'
    signing-policy-slug: 'macos-signing'
    artifact: 'dist/MeerK40t-macOS-Latest/MeerK40t.app'
    output-artifact-directory: 'signed'
```

### Requirements:
- Public GitHub repository
- SignPath account and GitHub app installation
- May have monthly signing limits on free tier

### Benefits:
- Fully automated signing through GitHub Actions
- Trusted certificates recognized by macOS
- No manual certificate management
- Professional CI/CD integration

## Option 6: Other Third-Party Code Signing Services

**Pros:** Various pricing models, different certificate types available
**Cons:** May require payment or have usage limits

Additional services to consider:

- **Sectigo Code Signing:** Offers certificates for various budgets
- **DigiCert Code Signing:** Enterprise-level code signing solutions
- **GlobalSign Code Signing:** International certificate authority
- **Comodo Code Signing:** Budget-friendly options

Most of these services offer both OV (Organization Validated) and EV (Extended Validation) certificates, with varying pricing tiers.

- **Default:** No code signing (app works but shows warnings)
- **File name:** `MeerK40t-macOS-Latest.dmg`
- **Distribution:** Users can still download and use the app

## For Production Distribution

For public distribution with proper code signing, consider:

1. Apple Developer Program ($99/year) for full distribution rights
2. Third-party code signing service
3. Notarization with Apple (requires paid developer account)

The current setup works for development and testing purposes.
