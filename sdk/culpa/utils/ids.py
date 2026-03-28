"""ULID generation utilities for Culpa event IDs."""

import random
import time


def generate_ulid() -> str:
    """
    Generate a ULID (Universally Unique Lexicographically Sortable Identifier).

    ULIDs are 26 characters, encode timestamp in first 10 chars and randomness
    in last 16 chars. They sort chronologically as strings.

    Returns:
        A 26-character ULID string.
    """
    # Crockford's base32 alphabet
    encoding = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

    # Timestamp component (48 bits = 10 chars)
    timestamp_ms = int(time.time() * 1000)
    timestamp_chars = []
    for _ in range(10):
        timestamp_chars.append(encoding[timestamp_ms & 0x1F])
        timestamp_ms >>= 5
    timestamp_chars.reverse()

    # Randomness component (80 bits = 16 chars)
    random_chars = [encoding[random.randint(0, 31)] for _ in range(16)]

    return "".join(timestamp_chars) + "".join(random_chars)
