/*
 * encryption.h - Header file for encryption.c
 *
 *              Omer Kfir (C)
 */

#ifndef ENCRYPTION_H
#define ENCRYPTION_H

#define KEY_MODE (256 / 8)
#define BLOCK_SIZE (16)

unsigned int randint(unsigned int, unsigned int);
unsigned int mod_pow(unsigned int, unsigned int, unsigned int);
void generate_diffie_numbers();
bool get_shared_secret(unsigned int);
int derive_key_from_secret(unsigned int, u8 *);
static size_t pkcs7_pad(const u8 *, size_t, size_t, u8 *);
int aes_cbc_encrypt_padded(const u8 *, size_t, u8 *, size_t *);

/* ENCRYPTION_H */
#endif