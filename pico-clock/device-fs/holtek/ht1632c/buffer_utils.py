import struct

def pack_num_bits(buffer: bytearray, offset_bytes: int, num_bits: int):
    struct.pack_into(">I", buffer, offset_bytes, num_bits - 1)

def pack_bitvector(bitstr: str, buffer: bytearray, bit_offset: int = 0) -> None:
    for i, bit in enumerate(bitstr):
        absolute_bit_index = bit_offset + i
        byte_index = (absolute_bit_index // 8)
        bit_index  = 7-(absolute_bit_index & 7)
        bit_mask = (1 << bit_index)
        bit_value = 1 if bit == "1" else 0
        # print(buffer)
        # print(buffer[byte_index])
        buffer[byte_index] = (buffer[byte_index] & ~bit_mask) | (bit_value << bit_index)
