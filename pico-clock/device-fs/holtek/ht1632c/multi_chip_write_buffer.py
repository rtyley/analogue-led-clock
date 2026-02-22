
from holtek.ht1632c.buffer_utils import pack_num_bits, pack_bitvector
from holtek.ht1632c.operations import WriteMode

class MultiChipWriteBuffer:
    def __init__(self, pixels_per_chip: list[int]):
        assert(not any(chip_pixels % 4 != 0 for chip_pixels in pixels_per_chip))
        self.pixels_per_chip = pixels_per_chip
        num_write_mode_header_bits = len(WriteMode.header_zero)
        num_chips = len(pixels_per_chip)
        self.total_pixels = sum(pixels_per_chip)

        total_bitvectors_size = self.total_pixels + (num_write_mode_header_bits * num_chips)
        self.header_bytes_required = (num_chips * 4)
        self.bitfield_bytes_required = (4 * ((total_bitvectors_size + 31) >> 5))
        bytes_required = self.header_bytes_required + self.bitfield_bytes_required

        self.raw_bytearray = bytearray(bytes_required)
        self._pixel_base_bit_offset_per_chip = [0] * num_chips

        self._num_header_bits = self.header_bytes_required * 8
        absolute_bit_offset = self._num_header_bits
        for chip_index, num_chip_pixels in enumerate(pixels_per_chip):
            num_chip_bits = num_write_mode_header_bits + num_chip_pixels
            pack_num_bits(self.raw_bytearray, chip_index * 4, num_chip_bits)
            pack_bitvector(WriteMode.header_zero, self.raw_bytearray, absolute_bit_offset)
            print(f"WriteMode header at {absolute_bit_offset//8}:{absolute_bit_offset%8}")
            self._pixel_base_bit_offset_per_chip[chip_index] = absolute_bit_offset + num_write_mode_header_bits
            absolute_bit_offset += (num_chip_bits)

        self.lows = [8] * self.bitfield_bytes_required
        self.highs = [0] * self.bitfield_bytes_required
        self.base_led_index_for_bytes = [0] * self.bitfield_bytes_required

        for led_id in range(self.total_pixels):
            bo = self.absolute_bit_offset_for_led_id(led_id)
            byte_metadata_index = (bo // 8) - self.header_bytes_required
            bit_index = bo % 8
            self.lows[byte_metadata_index] = min(self.lows[byte_metadata_index], bit_index)
            self.highs[byte_metadata_index] = max(self.highs[byte_metadata_index], bit_index + 1)
            self.base_led_index_for_bytes[byte_metadata_index] = led_id - bit_index

    def set_only(self, led_list: list[int]):
        led_list_index = 0
        num_leds_set = len(led_list)

        for byte_metadata_index in range(self.bitfield_bytes_required):
            high_exc = self.highs[byte_metadata_index]
            low_inc = self.lows[byte_metadata_index]
            if high_exc > low_inc:
                base_led_index_for_byte = self.base_led_index_for_bytes[byte_metadata_index]
                byte_index = byte_metadata_index + self.header_bytes_required
                background_mask = 0xFF & ~((1 << (8-low_inc)) - (1 << (8-high_exc)))
                current_bits = self.raw_bytearray[byte_index]
                bit_value = current_bits & background_mask
                # print(f"{byte_metadata_index}: {high_exc}-{low_inc} ({background_mask:08b}) : {current_bits:08b} {bit_value:08b}")
                if led_list_index < num_leds_set and led_list[led_list_index] < base_led_index_for_byte + 8:
                    for bit_index in range(low_inc, high_exc):
                        if led_list_index < num_leds_set and base_led_index_for_byte + bit_index == led_list[led_list_index]:
                            led_list_index += 1
                            bit_value += 1 << (7-bit_index)
                self.raw_bytearray[byte_index] = bit_value

    def write_pixel(self, led_id: int, value: bool):
        self.write_bitvector("1" if value else "0", self.absolute_bit_offset_for_led_id(led_id))

    def correctness_test(self):
        initial = bytearray(self.raw_bytearray)
        for led_id in range(self.total_pixels):
            print(f"Checking led_id={led_id}")
            assert self.raw_bytearray == initial
            self.write_pixel(led_id, True)
            expected = bytearray(self.raw_bytearray)
            self.write_pixel(led_id, False)
            assert self.raw_bytearray == initial
            self.set_only([led_id])
            for byte_index, actual_byte in enumerate(self.raw_bytearray):
                expected_byte = expected[byte_index]
                if actual_byte != expected_byte:
                    print(f"MISMATCH: led_id={led_id}, byte_index={byte_index}, {actual_byte:08b} != {expected_byte:08b}")
            self.write_pixel(led_id, False)



    def absolute_bit_offset_for_led_id(self, led_id: int) -> int:
        assert 0 <= led_id < self.total_pixels
        pixel_index = led_id
        for chip_index, num_chip_pixels in enumerate(self.pixels_per_chip):
            if pixel_index < num_chip_pixels:
                return self.absolute_bit_offset_for(chip_index, pixel_index)
            else:
                pixel_index -= num_chip_pixels
        return -1

    def write_chip_pixel(self, chip_index: int, pixel_index: int, value: bool):
        self.write_bitvector("1" if value else "0", self.absolute_bit_offset_for(chip_index, pixel_index))

    def absolute_bit_offset_for(self, chip_index, pixel_index) -> int:
        return self._pixel_base_bit_offset_per_chip[chip_index] + pixel_index

    def write_bitvector(self, bitstr: str, absolute_bit_offset_within_buffer: int):
        # print(f'absolute_bit_offset_within_buffer={absolute_bit_offset_within_buffer} bitstr="{bitstr}" buffer_bit_length={len(self.raw_bytearray) * 8}')
        pack_bitvector(bitstr, self.raw_bytearray, absolute_bit_offset_within_buffer)
