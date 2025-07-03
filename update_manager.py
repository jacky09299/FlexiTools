import json
import os
import sys # Ensure sys is imported for path detection
import time
import logging
from typing import Optional

# Configure logging for the update manager
logger = logging.getLogger(__name__) # Changed from __name__ to a fixed name for consistency
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Configuration ---
APP_NAME = "FlexiTools"

def get_user_writable_data_path(app_name: str = APP_NAME) -> Optional[str]:
    """
    Returns a user-specific writable directory path for application data.
    Creates the directory (app_name) and a 'saves' subdirectory within it if they don't exist.
    Example: %LOCALAPPDATA%\\FlexiTools or ~/.local/share/FlexiTools
    The 'saves' folder will be inside this path.
    """
    base_dir = ""
    if os.name == 'nt':  # Windows
        base_dir = os.getenv('LOCALAPPDATA', '')
    else:  # Linux, macOS
        # Use XDG Base Directory Specification if possible
        xdg_data_home = os.getenv('XDG_DATA_HOME')
        if xdg_data_home:
            base_dir = xdg_data_home
        else:
            base_dir = os.path.join(os.path.expanduser('~'), '.local', 'share')

    if not base_dir:
        logger.error(f"Could not determine base directory for user writable data.")
        return None

    app_data_path = os.path.join(base_dir, app_name)
    saves_path = os.path.join(app_data_path, "saves")

    try:
        os.makedirs(saves_path, exist_ok=True)
        logger.info(f"User writable saves path ensured: {saves_path}")
        return saves_path # Return the full path to the "saves" directory
    except OSError as e:
        logger.error(f"Error creating user writable saves directory {saves_path}: {e}")
        return None

SAVES_DIR = get_user_writable_data_path()

if SAVES_DIR is None:
    logger.critical("CRITICAL: User-specific SAVES_DIR could not be determined or created. Application settings and updates might not persist correctly.")
    # Define a fallback to current directory for critical failure, though this is not ideal for deployed app
    # This fallback is mainly for cases where system calls to get user dirs fail unexpectedly.
    fallback_saves_dir = os.path.join(os.getcwd(), "fallback_saves_data", "saves")
    logger.warning(f"Attempting to use fallback saves directory: {fallback_saves_dir}")
    try:
        os.makedirs(fallback_saves_dir, exist_ok=True)
        SAVES_DIR = fallback_saves_dir
    except Exception as e:
        logger.error(f"Failed to create fallback SAVES_DIR in current directory: {e}")
        SAVES_DIR = os.path.join(".", "saves") # Absolute last resort, likely problematic
        try:
            os.makedirs(SAVES_DIR, exist_ok=True)
        except:
             logger.error(f"Failed even to create ./saves. Update info persistence will fail.")
             SAVES_DIR = None


UPDATE_INFO_FILENAME = "update_info.json"
# UPDATE_INFO_PATH will be None if SAVES_DIR is None
UPDATE_INFO_PATH = os.path.join(SAVES_DIR, UPDATE_INFO_FILENAME) if SAVES_DIR else None


# version.txt is expected to be in the root of the installation, alongside the .exe
# or in a known location relative to the .exe (e.g., _internal/version.txt)
# For PyInstaller, if main.py changes CWD to sys._MEIPASS,
# then a version.txt placed in the same dir as main.py by the build process
# would be accessible directly by name.
# However, the NSI script defines PRODUCT_VERSION "1.0.0".
# Let's assume version.txt is in the *installation root*, one level above where the .exe might be if it's in a subfolder,
# or next to the .exe.
# If main.py does os.chdir(sys._MEIPASS), then to get to the exe's dir:
# For version.txt, it's more reliable to get it relative to the executable's actual location
def get_executable_path():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable) # Actual dir of FlexiTools.exe
    return os.path.dirname(os.path.abspath(__file__)) # Script dir for dev

APP_ROOT_PATH = get_executable_path()
VERSION_FILENAME = "version.txt"
# Assumption: version.txt is placed by the installer in the same directory as the executable
# or, if the executable is in a subfolder of the installation (e.g. bin/), then version.txt is in the root.
# Given the NSI structure, FlexiTools.exe is at $INSTDIR\FlexiTools.exe
# So version.txt should be at $INSTDIR\version.txt
VERSION_FILE_PATH = os.path.join(APP_ROOT_PATH, VERSION_FILENAME)


DEFAULT_VERSION = "0.0.0"

# --- Version Reading ---
def get_current_version() -> str:
    """
    Reads the current application version from version.txt.
    This file is expected to be created by the installer.
    """
    try:
        # Adjust path if version.txt is located elsewhere, e.g., inside _internal
        # For now, assuming it's next to the executable or in the CWD set by main.py if bundled.
        # If main.py sets CWD to sys._MEIPASS, and version.txt is also in MEIPASS, this works.
        # If version.txt is next to EXE, need os.path.dirname(sys.executable)

        version_file_to_check = VERSION_FILE_PATH # Default

        # If running from source and version.txt is not in script dir,
        # we might need a dev-specific location or a placeholder.
        if not (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')):
            # Development mode: check if a local dev version.txt exists
            dev_version_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), VERSION_FILENAME)
            if os.path.exists(dev_version_path):
                version_file_to_check = dev_version_path
            else:
                logger.warning(f"Development mode: {VERSION_FILENAME} not found at {dev_version_path} or {VERSION_FILE_PATH}. Using default version {DEFAULT_VERSION}.")
                return DEFAULT_VERSION

        if not os.path.exists(version_file_to_check):
            logger.warning(f"{VERSION_FILENAME} not found at {version_file_to_check}. Using default version {DEFAULT_VERSION}.")
            return DEFAULT_VERSION

        with open(version_file_to_check, "r", encoding="utf-8") as f:
            version = f.read().strip()
            if not version:
                logger.warning(f"{VERSION_FILENAME} is empty. Using default version {DEFAULT_VERSION}.")
                return DEFAULT_VERSION
            logger.info(f"Current version read from {version_file_to_check}: {version}")
            return version
    except Exception as e:
        logger.error(f"Error reading version from {VERSION_FILE_PATH}: {e}. Using default version {DEFAULT_VERSION}.")
        return DEFAULT_VERSION

def save_installed_version(version_str: str):
    """
    Saves the given version string to version.txt.
    This should be called after a successful update.
    """
    try:
        # Ensure the directory exists (it should, if the app is installed)
        os.makedirs(os.path.dirname(VERSION_FILE_PATH), exist_ok=True)
        with open(VERSION_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(version_str)
        logger.info(f"Successfully wrote version {version_str} to {VERSION_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error writing version to {VERSION_FILE_PATH}: {e}")
        return False

# --- Update Information (Timestamp, URL) ---
def get_update_info() -> dict:
    """
    Reads update information (last check timestamp, available update URL) from update_info.json.
    Returns a dictionary like:
    {
        "last_check_timestamp": float | None,
        "available_update": { "version": str, "url": str } | None
    }
    """
    if not UPDATE_INFO_PATH:
        logger.error("UPDATE_INFO_PATH is not set. Cannot get update info.")
        return {"last_check_timestamp": None, "available_update": None}

    default_info = {"last_check_timestamp": None, "available_update": None}
    if not os.path.exists(UPDATE_INFO_PATH):
        logger.info(f"{UPDATE_INFO_FILENAME} not found. Returning default info.")
        return default_info

    try:
        with open(UPDATE_INFO_PATH, "r", encoding="utf-8") as f:
            info = json.load(f)
            # Validate structure slightly
            if "last_check_timestamp" not in info:
                info["last_check_timestamp"] = None
            if "available_update" not in info:
                info["available_update"] = None
            logger.info(f"Update info loaded from {UPDATE_INFO_PATH}: {info}")
            return info
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {UPDATE_INFO_PATH}: {e}. Returning default info.")
        # Ensure file is closed if it was opened, though 'with open' handles this.
        # If the file is corrupt, we might want to back it up and create a new default one.
        return default_info
    except Exception as e:
        logger.error(f"General error reading {UPDATE_INFO_PATH}: {e}. Returning default info.")
        return default_info

def save_update_info(last_check_timestamp: float = None, available_update_data: dict = None):
    """
    Saves the last update check timestamp and available update data to update_info.json.
    Args:
        last_check_timestamp (float, optional): Unix timestamp of the last check.
        available_update_data (dict, optional): Dict with "version" and "url" if update is available.
                                                Pass None to clear existing available update.
    """
    if not UPDATE_INFO_PATH:
        logger.error("UPDATE_INFO_PATH is not set. Cannot save update info.")
        return

    current_info = get_update_info() # Load existing to preserve parts not being updated

    if last_check_timestamp is not None:
        current_info["last_check_timestamp"] = last_check_timestamp

    # If available_update_data is explicitly passed (even if None), update it.
    # If it's not passed, keep the existing value.
    if available_update_data is not None or ("available_update" in current_info and available_update_data is None) :
         current_info["available_update"] = available_update_data


    try:
        # Ensure SAVES_DIR exists
        if SAVES_DIR and not os.path.exists(SAVES_DIR):
            try:
                os.makedirs(SAVES_DIR)
                logger.info(f"Created directory for update info: {SAVES_DIR}")
            except OSError as e:
                logger.error(f"Could not create directory {SAVES_DIR} for update_info.json: {e}")
                return


        with open(UPDATE_INFO_PATH, "w", encoding="utf-8") as f:
            json.dump(current_info, f, indent=4)
        logger.info(f"Update info saved to {UPDATE_INFO_PATH}: {current_info}")
    except Exception as e:
        logger.error(f"Error writing to {UPDATE_INFO_PATH}: {e}")

# --- Utility ---
def is_time_to_check(hours_interval=24) -> bool:
    """Checks if it's time to check for updates based on the last check timestamp."""
    info = get_update_info()
    last_check = info.get("last_check_timestamp")
    if last_check is None:
        logger.info("No last check timestamp found. Time to check.")
        return True

    elapsed_seconds = time.time() - last_check
    interval_seconds = hours_interval * 60 * 60

    if elapsed_seconds >= interval_seconds:
        logger.info(f"Time to check for updates. Last check: {elapsed_seconds / 3600:.2f} hours ago.")
        return True
    else:
        logger.info(f"Not time to check yet. Last check: {elapsed_seconds / 3600:.2f} hours ago (Interval: {hours_interval}h).")
        return False

# Example usage (for testing this module directly)
if __name__ == "__main__":
    import sys # Required for getattr(sys, 'frozen', False) etc. in get_app_data_dir

    # --- Test version.txt handling ---
    print(f"Attempting to read version from: {VERSION_FILE_PATH}")
    # Create a dummy version.txt for testing if it doesn't exist
    if not os.path.exists(VERSION_FILE_PATH):
        print(f"Creating dummy {VERSION_FILENAME} for testing...")
        save_installed_version("1.0.0-test")

    current_version = get_current_version()
    print(f"Current version: {current_version}")

    # Test saving a new version
    # save_installed_version("1.0.1-test-update")
    # current_version = get_current_version()
    # print(f"Updated version: {current_version}")


    # --- Test update_info.json handling ---
    print(f"\nAttempting to read/write update_info from/to: {UPDATE_INFO_PATH}")
    if not UPDATE_INFO_PATH:
        print("UPDATE_INFO_PATH is not set, skipping update_info tests.")
    else:
        # Initial read
        info = get_update_info()
        print(f"Initial update info: {info}")

        # Test saving timestamp
        save_update_info(last_check_timestamp=time.time())
        info = get_update_info()
        print(f"Info after saving timestamp: {info}")

        # Test saving available update
        new_update_data = {"version": "1.2.0-test", "url": "http://example.com/update.exe"}
        save_update_info(available_update_data=new_update_data)
        info = get_update_info()
        print(f"Info after saving new update data: {info}")

        # Test clearing available update
        save_update_info(available_update_data=None) # Explicitly clear
        info = get_update_info()
        print(f"Info after clearing update data: {info}")

        # Test time_to_check
        print(f"\nIs it time to check (24h interval)? {is_time_to_check(24)}")

        # Simulate time passing (by setting an old timestamp)
        one_day_ago = time.time() - (25 * 60 * 60) # 25 hours ago
        save_update_info(last_check_timestamp=one_day_ago)
        info = get_update_info()
        print(f"Info after setting timestamp to 1 day ago: {info}")
        print(f"Is it time to check now (24h interval)? {is_time_to_check(24)}")

        # Clean up dummy update_info.json if created
        # if os.path.exists(UPDATE_INFO_PATH):
        #     os.remove(UPDATE_INFO_PATH)
        #     print(f"Cleaned up {UPDATE_INFO_PATH}")

    # Clean up dummy version.txt
    # if "test" in current_version and os.path.exists(VERSION_FILE_PATH):
    #    os.remove(VERSION_FILE_PATH)
    #    print(f"Cleaned up dummy {VERSION_FILENAME}")

    print("\nNote: For bundled app, paths might resolve differently. Test within bundled app.")
    print(f"VERSION_FILE_PATH resolved to: {VERSION_FILE_PATH}")
    print(f"UPDATE_INFO_PATH resolved to: {UPDATE_INFO_PATH}")
    print(f"SAVES_DIR resolved to: {SAVES_DIR}")
    print(f"APP_ROOT_PATH resolved to: {APP_ROOT_PATH}")

    # Test get_app_data_dir directly
    class MockSys:
        pass

    mock_sys_dev = MockSys()
    setattr(mock_sys_dev, 'frozen', False)

    # Temporarily replace sys for testing get_app_data_dir logic
    real_sys = sys
    sys = mock_sys_dev
    print(f"\nSAVES_DIR (dev mode emulated): {get_app_data_dir()}")

    mock_sys_frozen = MockSys()
    setattr(mock_sys_frozen, 'frozen', True)
    setattr(mock_sys_frozen, '_MEIPASS', "/tmp/_MEIPASS_dummy") # Dummy MEIPASS
    # Need to mock os.getcwd for frozen mode as main.py changes it
    real_getcwd = os.getcwd
    os.getcwd = lambda: getattr(sys, '_MEIPASS', real_getcwd())
    sys.executable = "/tmp/FlexiTools/FlexiTools.exe" # Dummy executable path

    sys = mock_sys_frozen
    print(f"SAVES_DIR (frozen mode emulated with CWD as MEIPASS): {get_app_data_dir()}")
    print(f"APP_ROOT_PATH (frozen mode emulated): {get_executable_path()}")
    print(f"VERSION_FILE_PATH (frozen mode emulated): {os.path.join(get_executable_path(), VERSION_FILENAME)}")

    os.getcwd = real_getcwd # Restore
    sys = real_sys # Restore

# --- GitHub API Interaction ---
GITHUB_API_URL = "https://api.github.com/repos/jacky09299/FlexiTools/releases/latest"
INSTALLER_ASSET_NAME = "FlexiToolsInstaller.exe"

def fetch_latest_release_info(api_url: str = GITHUB_API_URL) -> Optional[dict]:
    """
    Fetches the latest release information from the GitHub API.

    Args:
        api_url (str): The GitHub API URL for the latest release.

    Returns:
        dict: A dictionary with "version" and "url" if successful, otherwise None.
              Example: {"version": "1.1.0", "url": "download_url"}
              Version string directly from tag_name, may include 'v'.
    """
    try:
        import requests # Ensure requests is imported here, as it's an optional dependency for the project

        logger.info(f"Fetching latest release info from {api_url}")
        response = requests.get(api_url, timeout=10) # 10-second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

        data = response.json()
        tag_name = data.get("tag_name")
        if not tag_name:
            logger.error("Could not find 'tag_name' in API response.")
            return None

        assets = data.get("assets", [])
        download_url = None
        for asset in assets:
            if asset.get("name") == INSTALLER_ASSET_NAME:
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            logger.error(f"Could not find asset '{INSTALLER_ASSET_NAME}' in API response assets.")
            return None

        logger.info(f"Latest release found: version {tag_name}, url {download_url}")
        return {"version": tag_name, "url": download_url}

    except ImportError:
        logger.error("The 'requests' library is required for fetching updates but is not installed.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching release info: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON response from API: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching release info: {e}")
        return None

if __name__ == "__main__":
    # ... (previous __main__ content)

    # --- Test GitHub API Interaction ---
    print("\n--- Testing GitHub API Interaction ---")
    # Ensure requests is installed if you run this directly for testing
    # You might need to pip install requests in your environment
    # release_info = fetch_latest_release_info() # Test this carefully to avoid hitting API limits
    # if release_info:
    # print(f"Successfully fetched release info: {release_info}")
    # else:
    # print("Failed to fetch release info. Check logs for details.")
    # pass # Pass for now to avoid accidental API calls during repeated testing

    print("\n--- Testing Version Comparison ---")
    print(f"compare_versions('1.0.0', '1.0.1'): {compare_versions('1.0.0', '1.0.1')} (Expected: -1)")
    print(f"compare_versions('1.0.1', '1.0.0'): {compare_versions('1.0.1', '1.0.0')} (Expected: 1)")
    print(f"compare_versions('1.0.0', '1.0.0'): {compare_versions('1.0.0', '1.0.0')} (Expected: 0)")
    print(f"compare_versions('v1.2.0', '1.2.0'): {compare_versions('v1.2.0', '1.2.0')} (Expected: 0)")
    print(f"compare_versions('1.2.0', 'v1.2.1'): {compare_versions('1.2.0', 'v1.2.1')} (Expected: -1)")
    print(f"compare_versions('1.10.0', '1.2.0'): {compare_versions('1.10.0', '1.2.0')} (Expected: 1)")
    print(f"compare_versions('1.2.3', '1.2.3'): {compare_versions('1.2.3', '1.2.3')} (Expected: 0)")
    print(f"compare_versions('1.0', '1.0.0'): {compare_versions('1.0', '1.0.0')} (Expected: -1)")
    print(f"compare_versions('1.0.0', '1.0'): {compare_versions('1.0.0', '1.0')} (Expected: 1)")
    print(f"compare_versions('2.0', '1.9.9'): {compare_versions('2.0', '1.9.9')} (Expected: 1)")
    print(f"compare_versions('v0.9.0', '0.10.0'): {compare_versions('v0.9.0', '0.10.0')} (Expected: -1)")


    print("\n--- Testing Update Check Logic ---")
    # Mocking dependencies for check_for_updates would be ideal for robust testing.
    # For now, we can test parts or run it carefully.
    # print("Initial check_for_updates(force_check=True) run:")
    # status = check_for_updates(force_check=True) # Use force_check to bypass time limit for testing
    # print(f"Status: {status}")
    # print(f"Update info: {get_update_info()}")

    # print("\nSecond check_for_updates() run (should be rate limited if not forced):")
    # status_rate_limited = check_for_updates()
    # print(f"Status (rate limited): {status_rate_limited}")


    print("\nNote: For bundled app, paths might resolve differently. Test within bundled app.")

# --- Update Check Logic ---

# Define constants for return status of check_for_updates
UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
NO_UPDATE_FOUND = "NO_UPDATE_FOUND"
CHECK_SKIPPED_RATE_LIMIT = "CHECK_SKIPPED_RATE_LIMIT"
CHECK_SKIPPED_ALREADY_PENDING = "CHECK_SKIPPED_ALREADY_PENDING" # Added status
ERROR_FETCHING = "ERROR_FETCHING"
ERROR_CONFIG = "ERROR_CONFIG" # For issues like missing version.txt or unwriteable update_info.json

def compare_versions(version1: str, version2: str) -> int:
    """
    Compares two version strings (e.g., "1.0.0", "v1.2.1").
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    Assumes semantic versioning like components (major.minor.patch).
    Handles leading 'v'. Parses components as integers.
    """
    v1_str = version1.lstrip('v')
    v2_str = version2.lstrip('v')

    # Attempt to use packaging.version for robust comparison if available
    try:
        from packaging.version import parse as parse_version
        pv1 = parse_version(v1_str)
        pv2 = parse_version(v2_str)
        if pv1 < pv2: return -1
        if pv1 > pv2: return 1
        return 0
    except ImportError:
        logger.warning("`packaging` library not found, falling back to simple version comparison. Consider adding `packaging` to dependencies for robust version handling.")
        # Fallback to simple comparison
        v1_parts = [int(p) for p in v1_str.split('.')]
        v2_parts = [int(p) for p in v2_str.split('.')]

        for i in range(max(len(v1_parts), len(v2_parts))):
            p1 = v1_parts[i] if i < len(v1_parts) else 0
            p2 = v2_parts[i] if i < len(v2_parts) else 0
            if p1 < p2: return -1
            if p1 > p2: return 1
        return 0

def check_for_updates(force_check: bool = False) -> str:
    """
    Checks for application updates.
    - Respects a 24-hour check interval unless force_check is True.
    - Fetches latest release info from GitHub.
    - Compares with current version.
    - Saves update info if a new version is found.
    - Always updates the last check timestamp if an API call is made or was due.

    Args:
        force_check (bool): If True, bypasses the 24-hour rate limit.

    Returns:
        str: A status code (e.g., UPDATE_AVAILABLE, NO_UPDATE_FOUND, etc.).
    """
    current_app_version = get_current_version()
    # If version.txt is missing AND current_app_version is the default (meaning it truly wasn't found)
    if not os.path.exists(VERSION_FILE_PATH) and current_app_version == DEFAULT_VERSION:
        logger.error(f"Critical error: {VERSION_FILENAME} not found at {VERSION_FILE_PATH}. Cannot determine current version.")
        # Do not update timestamp here as the basic app configuration is missing.
        return ERROR_CONFIG

    if not UPDATE_INFO_PATH:
        logger.error("Critical error: UPDATE_INFO_PATH is not configured. Cannot check for updates.")
        return ERROR_CONFIG # Should not happen if SAVES_DIR was resolved

    update_info_data = get_update_info()

    # Scenario: An update was previously found and user hasn't acted on it.
    if update_info_data.get("available_update") and not force_check:
        pending_version = update_info_data["available_update"]["version"]
        # Check if this pending update is still actually newer than current.
        # This handles edge cases like manual downgrade after an update was found.
        if compare_versions(pending_version, current_app_version) > 0:
            logger.info(f"Update to version {pending_version} is already known and pending. No new API check needed.")
            return UPDATE_AVAILABLE # It's still available and newer
        else:
            logger.info(f"Previously known update {pending_version} is no longer newer than current {current_app_version}. Clearing it.")
            # Clear the stale pending update but proceed to check if it's time
            save_update_info(last_check_timestamp=update_info_data.get("last_check_timestamp"), available_update_data=None)
            # Fall through to normal check if it's time

    # Scenario: Rate limiting
    if not force_check and not is_time_to_check():
        # If an update is already known (and re-verified above as still newer), return that.
        # Otherwise, it's genuinely rate-limited.
        if update_info_data.get("available_update") and \
           compare_versions(update_info_data["available_update"]["version"], current_app_version) > 0:
            return UPDATE_AVAILABLE
        logger.info("Update check skipped due to rate limit (24-hour interval not passed).")
        return CHECK_SKIPPED_RATE_LIMIT

    logger.info(f"Proceeding with update check. Current version: {current_app_version}. Force check: {force_check}")

    latest_release = fetch_latest_release_info()
    timestamp_now = time.time()

    if not latest_release:
        logger.warning("Failed to fetch latest release information from API.")
        # Save timestamp even if fetch failed, to respect rate limiting for next attempt
        save_update_info(last_check_timestamp=timestamp_now, available_update_data=update_info_data.get("available_update")) # Preserve existing available_update if any
        return ERROR_FETCHING

    latest_api_version = latest_release["version"]
    download_url = latest_release["url"]

    logger.info(f"Current version: {current_app_version}, Latest version from API: {latest_api_version}")

    comparison_result = compare_versions(latest_api_version, current_app_version)

    if comparison_result > 0: # latest_api_version > current_app_version
        logger.info(f"Newer version {latest_api_version} found (current: {current_app_version}).")
        new_update_payload = {"version": latest_api_version, "url": download_url}
        save_update_info(last_check_timestamp=timestamp_now, available_update_data=new_update_payload)
        return UPDATE_AVAILABLE
    else: # latest_api_version <= current_app_version
        if comparison_result == 0:
            logger.info(f"Current version {current_app_version} is up to date.")
        else: # comparison_result < 0
            logger.warning(f"Latest version from API ({latest_api_version}) is older than current version ({current_app_version}). This is unusual but handled as 'no update'.")

        # Clear any previously stored available_update if current is up-to-date or newer
        save_update_info(last_check_timestamp=timestamp_now, available_update_data=None)
        return NO_UPDATE_FOUND
