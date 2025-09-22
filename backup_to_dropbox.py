import dropbox
import os
from secure_credentials import SecureCredentialManager

# --- CONFIGURATION ---
# The path to the local database file you want to back up.
LOCAL_DB_PATH = "cyt_history.db"
# The path where the file will be saved in your Dropbox App folder.
DROPBOX_DEST_PATH = f"/{LOCAL_DB_PATH}" 

def main():
    """
    Connects to Dropbox and uploads the history database.
    """
    print("--- Starting Dropbox Backup ---")

    # 1. Retrieve the secure API token
    print("Retrieving secure Dropbox API token...")
    # This will prompt for your master password
    manager = SecureCredentialManager()
    token = manager.get_credential("dropbox", "api_token")

    if not token:
        print("❌ ERROR: Could not retrieve Dropbox API token. Please run store_token.py first.")
        return

    if token == "INVALID_PASSWORD":
        print("❌ ERROR: Invalid master password. Could not decrypt Dropbox token.")
        return

    # 2. Check if the local database file exists
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"⚠️  WARNING: Local database file '{LOCAL_DB_PATH}' not found. Nothing to back up.")
        return

    # 3. Connect to Dropbox and upload the file
    try:
        print(f"Connecting to Dropbox and uploading '{LOCAL_DB_PATH}'...")
        with open(LOCAL_DB_PATH, "rb") as f:
            # Use the token to create a Dropbox client
            dbx = dropbox.Dropbox(token)
            # Upload the file, overwriting if it already exists
            dbx.files_upload(f.read(), DROPBOX_DEST_PATH, mode=dropbox.files.WriteMode('overwrite'))

        print(f"✅ SUCCESS: Successfully uploaded database to Dropbox.")

    except dropbox.exceptions.AuthError:
        print("❌ ERROR: Dropbox authentication failed. Your API token might be invalid or expired.")
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()