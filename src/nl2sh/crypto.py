import sys
import base64

def dpapi_encrypt(plaintext: str) -> str:
    """
    Encrypts plaintext string using Windows DPAPI (CryptProtectData).
    Returns a base64-encoded encrypted string.
    """
    if sys.platform != "win32":
        # Fallback for non-Windows (or simply base64 tagged)
        return "b64:" + base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    data_bytes = plaintext.encode("utf-8")
    blob_in = DATA_BLOB(
        len(data_bytes),
        ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte)),
    )
    blob_out = DATA_BLOB()

    # CryptProtectData(pDataIn, szDataDescr, pOptionalEntropy, pvReserved, pPromptStruct, dwFlags, pDataOut)
    # dwFlags = 0x01 (CRYPTPROTECT_UI_FORBIDDEN)
    ret = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        "nl2sh_key",
        None,
        None,
        None,
        0x01,
        ctypes.byref(blob_out),
    )

    if not ret:
        raise RuntimeError("Windows DPAPI encryption failed.")

    try:
        raw_encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return "dpapi:" + base64.b64encode(raw_encrypted).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def dpapi_decrypt(encrypted_str: str) -> str:
    """
    Decrypts base64-encoded encrypted string using Windows DPAPI (CryptUnprotectData).
    """
    if not encrypted_str:
        return ""

    if encrypted_str.startswith("b64:"):
        return base64.b64decode(encrypted_str[4:]).decode("utf-8")

    if not encrypted_str.startswith("dpapi:"):
        # Not encrypted, return as is (backwards compatibility)
        return encrypted_str

    if sys.platform != "win32":
        raise RuntimeError("Cannot decrypt Windows DPAPI data on non-Windows platform.")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    raw_encrypted = base64.b64decode(encrypted_str[6:])
    blob_in = DATA_BLOB(
        len(raw_encrypted),
        ctypes.cast(ctypes.create_string_buffer(raw_encrypted), ctypes.POINTER(ctypes.c_byte)),
    )
    blob_out = DATA_BLOB()

    ret = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0x01,
        ctypes.byref(blob_out),
    )

    if not ret:
        raise RuntimeError("Windows DPAPI decryption failed.")

    try:
        decrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return decrypted_bytes.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
