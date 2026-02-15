
from holtek.ht1632c.buffer_utils import pack_num_bits, pack_bitvector
from holtek.ht1632c.operations import WriteMode

class MultiChipWriteBuffer:
    def __init__(self, pixels_per_chip: list[int]):
        self.pixels_per_chip = pixels_per_chip
        num_write_mode_header_bits = len(WriteMode.header_zero)
        num_chips = len(pixels_per_chip)
        self.total_pixels = sum(pixels_per_chip)

        total_bitvectors_size = self.total_pixels + (num_write_mode_header_bits * num_chips)
        header_bytes_required = (num_chips * 4)
        bytes_required = header_bytes_required + (4 * ((total_bitvectors_size + 31) >> 5))

        self.raw_bytearray = bytearray(bytes_required)
        self._pixel_base_bit_offset_per_chip = [0] * num_chips

        self._num_header_bits = header_bytes_required * 8
        absolute_bit_offset = self._num_header_bits
        for chip_index, num_chip_pixels in enumerate(pixels_per_chip):
            num_chip_bits = num_write_mode_header_bits + num_chip_pixels
            pack_num_bits(self.raw_bytearray, chip_index * 4, num_chip_bits)
            pack_bitvector(WriteMode.header_zero, self.raw_bytearray, absolute_bit_offset)
            self._pixel_base_bit_offset_per_chip[chip_index] = absolute_bit_offset + num_write_mode_header_bits
            absolute_bit_offset += (num_chip_bits)

    def write_pixel(self, absolute_pixel_index: int, value: bool):
        assert 0 <= absolute_pixel_index < self.total_pixels
        pixel_index = absolute_pixel_index
        for chip_index, num_chip_pixels in enumerate(self.pixels_per_chip):
            if pixel_index < num_chip_pixels:
                self.write_chip_pixel(chip_index, pixel_index, value)
                return
            else:
                pixel_index -= num_chip_pixels

    def write_chip_pixel(self, chip_index: int, pixel_index: int, value: bool):
        pixel_base_offset_for_chip = self._pixel_base_bit_offset_per_chip[chip_index]
        # print(f'chip_index={chip_index} pixel_index={pixel_index} pixel_base_offset_for_chip={pixel_base_offset_for_chip} bit_offset={bit_offset}')
        self.write_bitvector("1" if value else "0", pixel_base_offset_for_chip + pixel_index)

    def write_bitvector(self, bitstr: str, absolute_bit_offset_within_buffer: int):
        # print(f'absolute_bit_offset_within_buffer={absolute_bit_offset_within_buffer} bitstr="{bitstr}" buffer_bit_length={len(self.raw_bytearray) * 8}')
        pack_bitvector(bitstr, self.raw_bytearray, absolute_bit_offset_within_buffer)