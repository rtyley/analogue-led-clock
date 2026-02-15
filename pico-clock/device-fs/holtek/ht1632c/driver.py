import rp2
from rp2 import PIO
from machine import Pin
from time import sleep, ticks_us, ticks_diff
import struct
from holtek.ht1632c.buffer_utils import pack_num_bits, pack_bitvector

@rp2.asm_pio(set_init=[PIO.OUT_LOW] * 1, out_init=[PIO.OUT_LOW] * 1, sideset_init=[PIO.OUT_HIGH] * 3, autopull=True,
             fifo_join=PIO.JOIN_TX)
def dualHoltekHT1632C():
    wrap_target()
    label("init")
    pull(block).side(0b111)
    mov(x, osr)
    out(null, 32)

    pull(block)
    mov(y, osr)
    out(null, 32)

    jmp(not_x, "cs1_start")
    nop().side(0b101)  # 'tsu1' setup time for CS to WR clock width (300ns BEGINS)
    nop().delay(1)
    label("cs0_loop")
    out(pins, 1).side(0b100).delay(1)  # 'tsu' setup time for Data to WR clock width (100ns BEGINS)
    nop().delay(1)
    nop()
    nop().side(0b101)  # 'th' hold time for Data to WR clock width (200ns BEGINS)
    nop().delay(1)
    nop()
    jmp(x_dec, "cs0_loop")
    set(pins, 0)

    label("cs1_start")
    jmp(not_y, "init").side(0b111)
    nop().side(0b011)
    nop().delay(1)
    label("cs1_loop")
    out(pins, 1).side(0b010)
    nop().delay(1)
    nop().delay(1)
    nop().side(0b011)
    nop().delay(1)
    nop()
    jmp(y_dec, "cs1_loop")
    set(pins, 0)
    wrap()

def bytearray_to_bits(buf: bytearray) -> str:
    return " ".join(f"{b:08b}" for b in buf)

def join_bits_for_both_chips(bits_for_chips):
    all_bits_to_transmit = "".join(bits_for_chips)
    return all_bits_to_transmit

# Modelled after https://github.com/adafruit/Adafruit_CircuitPython_AW9523/blob/main/adafruit_aw9523.py
class HT1632C:

    def __init__(
            self, base_pin_index: int, state_machine_id: int, freq: int
    ) -> None:
        data_pin = Pin(base_pin_index, Pin.OUT)
        write_pin = Pin(base_pin_index + 1, Pin.OUT)
        cs1_pin = Pin(base_pin_index + 2, Pin.OUT)
        cs2_pin = Pin(base_pin_index + 3, Pin.OUT)
        self.sm = rp2.StateMachine(state_machine_id, dualHoltekHT1632C, freq=freq, set_base=data_pin, out_base=data_pin, sideset_base=write_pin)
        # self._buffer = bytearray(2)

        self.sm.active(False)
        sleep(0.1)
        assert not self.sm.active()
        assert self.sm.tx_fifo() == 0
        self.sm.active(1)

    # @timed_function
    def transmit(self, operations: list[Operation]):
        bits_for_chips: list[str] = self.convert_ops_to_bits(operations)
        self.transmit_bits_for_chips(bits_for_chips)

    def transmit_bits_for_chips(self, bits_for_chips):
        all_bits_to_transmit = join_bits_for_both_chips(bits_for_chips)

        num_bits_to_transmit = len(all_bits_to_transmit)
        bytes_required = 8 + (4 * ((num_bits_to_transmit + 31) >> 5))
        src_data = bytearray(bytes_required)
        pack_num_bits(src_data, 0, len(bits_for_chips[0]))
        pack_num_bits(src_data, 4, len(bits_for_chips[1]))
        pack_bitvector(all_bits_to_transmit, src_data, bit_offset=2 * 4 * 8)

        self.transmit_bytearray(src_data)

    def transmit_bytearray(self, src_data: bytearray):
        self.shut_down_statemachine_and_fifo()

        # pio_num is index of the PIO block being used, sm_num is the state machine in that block.
        # my_state_machine is an rp2.PIO() instance.
        pio_num = 0
        sm_num = 0
        DATA_REQUEST_INDEX = (pio_num << 3) + sm_num

        d = rp2.DMA()
        c = d.pack_ctrl(inc_write=False, treq_sel=DATA_REQUEST_INDEX, bswap=True)

        d.config(
            read=src_data,
            write=self.sm,
            count=len(src_data) // 4,
            ctrl=c,
            trigger=True
        )

        self.wait_for_fifo_to_empty()
        d.close()

    # @timed_function
    def shut_down_statemachine_and_fifo(self):
        self.sm.active(False)
        assert not self.sm.active()
        assert self.sm.tx_fifo() == 0

    # @timed_function
    def wait_for_fifo_to_empty(self):
        self.sm.active(True)
        while self.sm.tx_fifo() > 0:
            sleep(0.00001)
        assert self.sm.tx_fifo() == 0

    # @timed_function
    def convert_ops_to_bits(self, operations):
        return [op.bits() for op in operations]