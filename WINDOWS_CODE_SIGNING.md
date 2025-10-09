# Free Windows Code Signing Options for MeerK40t

> **Update (October 2025):** SSL.com's free code signing program for open source projects appears to be discontinued or the URL has changed. SignPath.io is now the recommended free alternative.

## Option 1: No Code Signing (Simplest - Default)

**Pros:** Free, no setup required
**Cons:** Windows shows "Unknown Publisher" warnings, may be blocked by antivirus

The workflow currently uses this approach by default.

## Option 2: Self-Signed Certificate (Free)

**Pros:** Free, provides basic code signing
**Cons:** Still shows warnings, not trusted by Windows

To enable:

1. Uncomment the self-signed certificate lines in the workflow
2. The workflow will create and use a self-signed certificate

## Option 3: SSL.com Code Signing

**Note:** SSL.com previously offered free code signing certificates for open source projects, but the program availability and URL may have changed. Please check SSL.com's current offerings.

**Pros:** Trusted certificates when available, professional code signing
**Cons:** Free program may no longer be available, requires account setup

### Current Status:
- Visit https://www.ssl.com/code-signing to check current code signing offerings
- Look for any free or discounted programs for open source projects
- Contact SSL.com support to inquire about free code signing options

### If Available - Setup Process:

1. **Check Current Program:**
   - Visit SSL.com's code signing page to see current offerings
   - Look for free or discounted options for open source projects

2. **Apply if Available:**
   - Fill out the application form for code signing certificates
   - Provide project details and GitHub repository link
   - Wait for approval

3. **Download Certificate:**
   - Once approved, download the code signing certificate (.p12 or .pfx file)
   - Note the certificate password provided

4. **Add to GitHub Secrets:**
   - Base64 encode the certificate file:
     ```bash
     base64 -i certificate.p12
     ```
   - Add to GitHub repository secrets:
     - `WINDOWS_CERTIFICATE_P12`: The base64 encoded certificate
     - `WINDOWS_CERTIFICATE_PASSWORD`: Certificate password
     - `WINDOWS_CERTIFICATE_NAME`: Certificate name (usually "SSL.com Code Signing")

5. **Update Workflow:**
   - Uncomment the SSL.com certificate lines in `.github/workflows/win-all.yml` and `win-minimal.yml`
   - The workflow will use the SSL.com certificate for code signing

## Option 4: SignPath.io Code Signing (Recommended Alternative)

**Pros:** Free for open source projects, automated GitHub integration, trusted certificates
**Cons:** Requires GitHub integration setup, limited to certain certificate types, Windows integration may require additional configuration

SignPath.io provides free code signing for open source projects through their GitHub integration.

### Setup Process:

1. **Create SignPath Account:**
   - Visit https://signpath.io
   - Sign up for a free account
   - Connect your GitHub repository

2. **Configure Signing Policy:**
   - Create a signing policy for Windows code signing
   - Choose certificate type (OV or EV, depending on free tier limits)
   - Configure GitHub Actions integration

3. **GitHub Integration:**
   - Install SignPath GitHub App in your repository
   - Add the following secrets to your GitHub repository:
     - `SIGNPATH_API_TOKEN`: Your SignPath API token
     - `SIGNPATH_ORG_ID`: Your SignPath organization ID
   - SignPath integration for Windows executables requires additional setup

### Note:
Windows SignPath integration is available but requires specific configuration for executable signing. Contact SignPath support for Windows-specific setup guidance.

### Requirements:
- Public GitHub repository
- SignPath account and GitHub app installation
- May have monthly signing limits on free tier

### Benefits:
- Fully automated signing through GitHub Actions
- Trusted certificates recognized by Windows
- No manual certificate management
- Professional CI/CD integration

## Option 5: Other Third-Party Code Signing Services

**Pros:** Various pricing models, different certificate types available
**Cons:** May require payment or have usage limits

Additional services to consider:

- **Sectigo Code Signing:** Offers certificates for various budgets
- **DigiCert Code Signing:** Enterprise-level code signing solutions
- **GlobalSign Code Signing:** International certificate authority
- **Comodo Code Signing:** Budget-friendly options

Most of these services offer both OV (Organization Validated) and EV (Extended Validation) certificates, with varying pricing tiers.

## Current Workflow Behavior

- **Default:** No code signing (app works but shows warnings)
- **File names:** `MeerK40t-all.exe` and `MeerK40t-minimal.exe`
- **Distribution:** Users can still download and use the app

## For Production Distribution

For public distribution with proper code signing, consider:

1. Third-party code signing service (recommended for open source)
2. Extended Validation (EV) certificates for highest trust level
3. Timestamping to ensure signatures remain valid after certificate expiry

The current setup works for development and testing purposes.
