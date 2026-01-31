# ESP3D Upload Feature for GRBL Devices

## Overview

The ESP3D upload feature allows MeerK40t to upload G-code files directly to network-connected GRBL laser controllers running ESP3D-WEBUI firmware. This enables wireless workflow where you can generate, upload, and execute laser jobs without needing a direct serial connection.

## Requirements

### Hardware Requirements
- GRBL-based laser controller with ESP3D firmware (e.g., ESP32 or ESP8266 based boards)
- ESP3D-WEBUI installed and configured
- SD card inserted in the ESP3D device
- Network connection to the ESP3D device

### Software Requirements
- MeerK40t with GRBL device driver
- Python `requests` library (automatically installed with MeerK40t)

## Configuration

### 1. Enable ESP3D Upload

1. Open your GRBL device configuration: **Device → Config → ESP3D Upload** tab
2. Check **"Enable ESP3D Upload"**
3. Configure connection settings:
   - **ESP3D Host**: IP address or hostname of your ESP3D device (e.g., `192.168.1.100`)
   - **ESP3D Port**: HTTP port (usually `80`)
   - **ESP3D SD Path**: Default path on SD card (usually `/`)

### 2. Optional Authentication

If your ESP3D device requires authentication:
1. Enter **Username** in the authentication section
2. Enter **Password** in the authentication section

### 3. Test Connection

1. Click **"Test Connection"** button in the ESP3D Upload panel
2. Verify successful connection and SD card information is displayed
3. Click **"List Files"** to view existing files on the SD card

## Usage

### Console Commands

MeerK40t provides several console commands for ESP3D operations:

#### Configure ESP3D Settings

```
esp3d_config                     # Show current configuration
esp3d_config test                # Test connection to ESP3D device
esp3d_config set host 192.168.1.100   # Set ESP3D host IP
esp3d_config set port 80         # Set ESP3D port
esp3d_config set enabled true    # Enable ESP3D upload
```

#### List Files on SD Card

```
esp3d_list                       # List all files on ESP3D SD card
```

#### Upload and Execute G-code

```
esp3d_upload_run                 # Generate G-code, upload, and optionally execute
esp3d_upload_run -f myfile.gc    # Upload with custom filename
esp3d_upload_run -e              # Upload and execute immediately
```

#### Execute Existing File

```
esp3d_run_file filename.gc       # Execute a file already on SD card
```

#### Delete Files

```
esp3d_delete filename.gc         # Delete a file from SD card
```

## Filename Conventions

### 8.3 Format (Recommended)

ESP3D and many SD card implementations work best with 8.3 format filenames:
- **8 characters** maximum for filename
- **3 characters** maximum for extension
- No spaces or special characters

**Examples:**
- ✅ `file0001.gc` - Valid
- ✅ `laser01.gco` - Valid
- ✅ `test.gc` - Valid
- ❌ `my laser file.gcode` - Too long, has spaces
- ❌ `verylongfilename.gc` - Filename too long

MeerK40t automatically generates 8.3 compliant filenames when no custom filename is provided.

## Workflow Examples

### Basic Upload Workflow

1. Design your laser project in MeerK40t
2. Generate operations (cut, engrave, etc.)
3. Execute in console:
   ```
   esp3d_upload_run -e
   ```
4. G-code is generated, uploaded to ESP3D, and execution starts automatically

### Advanced Workflow

1. Generate and upload without executing:
   ```
   esp3d_upload_run -f project1.gc
   ```
2. List files to verify upload:
   ```
   esp3d_list
   ```
3. Execute when ready:
   ```
   esp3d_run_file project1.gc
   ```

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to ESP3D device

**Solutions**:
1. Verify ESP3D device is on the network
2. Ping the IP address from your computer
3. Check firewall settings
4. Verify the port number (default: 80)
5. Try accessing `http://[ip-address]` in a web browser

### Authentication Errors

**Problem**: "Authentication failed" error

**Solutions**:
1. Verify username and password in ESP3D Upload settings
2. Check ESP3D web interface for authentication requirements
3. Some ESP3D versions don't require authentication - leave fields empty

### SD Card Issues

**Problem**: "SD card error" or "Cannot access SD card"

**Solutions**:
1. Verify the SD card is properly inserted in the ESP3D device
2. Check SD card format (FAT32 recommended)
3. Try reformatting the SD card
4. Check SD card capacity (some devices have limits)

### Upload Failures

**Problem**: Upload fails or times out

**Solutions**:
1. Check available space on SD card with `esp3d_list`
2. Verify network connection stability
3. Try smaller files first
4. Increase timeout in ESP3D settings if available

### File Not Executing

**Problem**: File uploads but doesn't execute

**Solutions**:
1. Verify G-code format is compatible with your GRBL version
2. Check ESP3D device logs
3. Try executing from ESP3D web interface to rule out MeerK40t issues
4. Verify filename is in 8.3 format

## Technical Details

### ESP3D API Endpoints

The feature uses these ESP3D-WEBUI HTTP endpoints:

- `GET /command?cmd=[ESP800]` - Test connection/get status
- `GET /sdfiles?path=/` - List files and SD card info
- `POST /sdfiles` - Upload file to SD card
- `GET /command?cmd=[ESP700]/sd/filename` - Execute G-code file
- `GET /sdfiles?action=delete&filename=file.gc` - Delete file

### File Size Limitations

- Maximum file size depends on SD card capacity
- ESP3D checks available space before upload
- Large files may take time to upload depending on network speed

### Security Considerations

- ESP3D authentication credentials are stored in MeerK40t settings
- Use authentication when operating on shared networks
- Consider network security when exposing ESP3D to the internet

## Future Enhancements

Potential future features:
- Progress bar for upload operations
- Batch file upload
- SD card file browser in GUI
- Print queue management
- Automatic file cleanup after successful execution
- OTA (Over-The-Air) firmware updates

## Related Documentation

- [ESP3D-WEBUI Documentation](https://github.com/luc-github/ESP3D-WEBUI)
- [GRBL Documentation](https://github.com/gnea/grbl/wiki)
- [MeerK40t GRBL Driver Documentation](../README.md)

## Testing with ESP3D Emulator

If you don't have an ESP3D device available for testing, MeerK40t includes an ESP3D emulator server.

### Starting the Emulator

**Windows PowerShell:**
```powershell
python -m meerk40t.grbl.esp3d_emulator
```

**With custom host/port:**
```powershell
python -m meerk40t.grbl.esp3d_emulator --host 0.0.0.0 --port 8080
```

### Configure MeerK40t for Emulator

1. Start the emulator (default: `localhost:8080`)
2. In MeerK40t, open **Device → Config → ESP3D Upload**
3. Configure settings:
   - **ESP3D Host**: `localhost` (or `127.0.0.1`)
   - **ESP3D Port**: `8080` (or your custom port)
   - **Enable ESP3D Upload**: Check this box
4. Click **Test Connection** to verify

### Emulator Features

The emulator provides:
- ✅ Connection testing (`[ESP800]` command)
- ✅ SD card information (simulated 2GB card)
- ✅ File upload to virtual SD card
- ✅ File listing with sizes and timestamps
- ✅ File deletion
- ✅ File execution simulation
- ✅ Web interface at `http://localhost:8080`

### Emulator Limitations

- Files are stored in memory (lost on restart)
- No actual G-code execution
- No authentication required (always accepts)
- Simplified responses compared to real ESP3D

### Using the Emulator for Testing

**Test the complete workflow:**
```
1. Start emulator: python -m meerk40t.grbl.esp3d_emulator
2. Configure MeerK40t with localhost:8080
3. Test connection from GUI
4. Upload a test file: esp3d_upload_run -f test.gc
5. List files: esp3d_list
6. Execute file: esp3d_run_file test.gc
7. Delete file: esp3d_delete test.gc
```

## Support

For issues specific to ESP3D upload:
1. Check this documentation
2. Test with the ESP3D emulator first
3. Verify ESP3D device is functioning correctly via web interface
4. Test with simple G-code files first
5. Report issues on MeerK40t GitHub repository

For ESP3D device issues:
- Visit [ESP3D GitHub repository](https://github.com/luc-github/ESP3D)
- Check ESP3D-WEBUI documentation
