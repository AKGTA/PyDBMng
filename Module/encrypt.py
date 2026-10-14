import bcrypt
import hmac
import hashlib
from debugger import debug

"""
Simulate .env file but it is a temporary permenenant key
"""
salt = b"$2b$12$ieYNkQp8QumgedUo30nuPO"
secret_shift = 5
secret_key = "AWHOWDIDYOUKNOW"
# SERVER SIDE ONLY: Keep this hidden in your server environment
MAC_VERIFICATION_KEY = b"man_I_think_you_over_done_it"

key = {
    "secret_shift" : secret_shift,
    "secret_key" : secret_key,
}

@debug("Hashing item securely",
       "This function hashes the input item using bcrypt with a predefined salt.",
       "It returns the hashed value which can be stored securely.")
def hash_item(item):
    enitem = item.encode()
    # Note: In production, generate a fresh salt every time via bcrypt.gensalt()
    hashed_item = bcrypt.hashpw(password=enitem, salt=salt)
    return hashed_item

@debug("Caesar Cipher",
       "This function applies the Caesar cipher to the input text.",
       "It supports both encryption and decryption based on the decrypt flag.")
def caesar_cipher(text, shift, decrypt=False):
    if decrypt:
        shift = -shift
    result = ""
    for char in text:
        result += chr(ord(char) + shift)
    return result

@debug("XOR Cipher",
       "This function applies the XOR cipher to the input text.",
       "It uses a key string to perform the encryption/decryption.")
def xor_cipher(text, key_str):
    if not key_str:
        return text
    # FIXED: Ensure key is a string so cycling works cleanly
    key_cycle = (key_str * (len(text) // len(key_str) + 1))[:len(text)]
    return "".join(chr(ord(t) ^ ord(k)) for t, k in zip(text, key_cycle))

@debug("Packing data securely with encryption and HMAC signature", 
       "This function encrypts the data and appends a secure HMAC signature for integrity verification.",
       "It uses both Caesar cipher and XOR cipher for encryption layers.")
def packing_data_securely(data, key_dict):
    # Run your original encryption layers
    encrypted_data = caesar_cipher(data, key_dict.get("secret_shift"))
    encrypted_data = xor_cipher(encrypted_data, key_dict.get("secret_key"))
    
    # Convert the ciphertext to bytes so we can sign it
    ciphertext_bytes = encrypted_data.encode('utf-8')
    
    # Generate a secure SHA256 signature over the encrypted text
    signature = hmac.new(MAC_VERIFICATION_KEY, ciphertext_bytes, hashlib.sha256).hexdigest()
    
    # Return a combined bundle string (Ciphertext + Separator + Signature)
    # Using a rare token separator like ':::' to avoid conflicts
    return f"{encrypted_data}:::{signature}"

@debug("Unpacking data securely with integrity check", 
       "This function verifies the HMAC signature before decrypting the data.",
       "If the signature does not match, it returns None to indicate tampering.")
def unpack_data(raw_bundle_string, key_dict):
    try:
        # Split the encrypted text from the signature safely
        if ":::" not in raw_bundle_string:
            return None # Missing signature completely
            
        encrypted_data, provided_signature = raw_bundle_string.split(":::", 1)
        ciphertext_bytes = encrypted_data.encode('utf-8')
        
        # Re-calculate what the expected signature should look like
        expected_signature = hmac.new(MAC_VERIFICATION_KEY, ciphertext_bytes, hashlib.sha256).hexdigest()
        
        # CRITICAL: Verify integrity BEFORE decrypting anything
        # compare_digest prevents timing attacks by checking strings at identical speeds
        if not hmac.compare_digest(provided_signature, expected_signature):
            print("SECURITY WARNING: Tampered data detected! Drop request instantly.")
            return None 
            
        # Safe to decrypt: Data is proven 100% genuine and untouched
        decrypted_data = xor_cipher(encrypted_data, key_dict.get("secret_key"))
        decrypted_data = caesar_cipher(decrypted_data, key_dict.get("secret_shift"), decrypt=True)

        return decrypted_data
        
    except Exception:
        # Catch-all to gracefully fail if any structural malformations occur
        return None


if __name__ == "__main__":
    # --- Quick Test ---
    # Example usage:
    message = "You've success!!"

    encrypted = xor_cipher(message, secret_key)
    decrypted = xor_cipher(encrypted, secret_key)  # XORing twice reverts it back
    debug("XOR Cipher Test", f"Encrypted: {repr(encrypted)}", f"Decrypted: {decrypted}")

    secret_message = "Hello, World!!"
    encrypted = caesar_cipher(secret_message, secret_shift)
    decrypted = caesar_cipher(encrypted, secret_shift, decrypt=True)
    debug("Caesar Cipher test", f"Encrypted: {encrypted}", f"Decrypted: {decrypted}")

    message = "Try guess my key"
    packed = packing_data_securely(message, key)
    unpacked = unpack_data(packed, key)
    debug("Packing/Unpacking Test", f"Packed: {packed}", f"Unpacked: {unpacked}")