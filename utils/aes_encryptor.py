import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class AES256FileEncryptor:
    def __init__(self):
        self.backend = default_backend()
        self.chunk_size = 64 * 1024  # 64KB chunks

    def generate_key_from_password(self, password: str, salt: bytes = None) -> tuple:
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        key = kdf.derive(password.encode('utf-8'))
        return key, salt

    def calculate_file_hash(self, file_path: str) -> str:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def encrypt_file(self, input_file: str, output_file: str, password: str) -> dict:
        try:
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"File not found: {input_file}")
            
            original_hash = self.calculate_file_hash(input_file)
            key, salt = self.generate_key_from_password(password)
            iv = os.urandom(16)
            file_size = os.path.getsize(input_file)
            
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(128).padder()

            with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
                outfile.write(salt)
                outfile.write(iv)
                outfile.write(original_hash.encode('utf-8'))
                outfile.write(file_size.to_bytes(8, byteorder='big'))
                
                while True:
                    chunk = infile.read(self.chunk_size)
                    if not chunk:
                        padded_chunk = padder.finalize()
                        if padded_chunk:
                            outfile.write(encryptor.update(padded_chunk))
                        break
                    elif len(chunk) < self.chunk_size:
                        padded_chunk = padder.update(chunk) + padder.finalize()
                        outfile.write(encryptor.update(padded_chunk))
                        break
                    else:
                        padded_chunk = padder.update(chunk)
                        outfile.write(encryptor.update(padded_chunk))
                
                final_chunk = encryptor.finalize()
                if final_chunk:
                    outfile.write(final_chunk)

            encrypted_size = os.path.getsize(output_file)
            return {
                'success': True,
                'original_size': file_size,
                'encrypted_size': encrypted_size,
                'original_hash': original_hash
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def decrypt_file(self, input_file: str, output_file: str, password: str) -> dict:
        try:
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"File not found: {input_file}")

            with open(input_file, 'rb') as infile:
                salt = infile.read(16)
                iv = infile.read(16)
                original_hash = infile.read(64).decode('utf-8')
                original_size = int.from_bytes(infile.read(8), byteorder='big')
                
                key, _ = self.generate_key_from_password(password, salt)
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
                decryptor = cipher.decryptor()
                unpadder = padding.PKCS7(128).unpadder()

                with open(output_file, 'wb') as outfile:
                    decrypted_data = b""
                    while True:
                        chunk = infile.read(self.chunk_size)
                        if not chunk:
                            break
                        decrypted_data += decryptor.update(chunk)
                    
                    decrypted_data += decryptor.finalize()
                    unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
                    outfile.write(unpadded_data[:original_size])

            decrypted_hash = self.calculate_file_hash(output_file)
            integrity_check = original_hash == decrypted_hash
            decrypted_size = os.path.getsize(output_file)
            
            return {
                'success': True,
                'original_size': original_size,
                'decrypted_size': decrypted_size,
                'integrity_check': integrity_check,
                'original_hash': original_hash,
                'decrypted_hash': decrypted_hash
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }