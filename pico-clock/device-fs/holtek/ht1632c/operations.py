class Operation:
    def bits(self) -> str:
        """Extract text from the currently loaded file."""
        pass

class WriteMode(Operation):
    def header(address: int) -> str:
        return f'101{address:07b}'

    header_zero: str = header(0)

    def __init__(self, address: int, data: list[int]):
        self.address = address
        self.data = data

    def bits(self) -> str:
        return WriteMode.header(self.address) + ("".join(("".join((reversed("{0:04b}".format(x)))) for x in self.data)))

class CommandMode(Operation):
    commands: list[int]

    def __init__(self, commands: list[int]):
        self.commands = commands

    def bits(self) -> str:
        return f'100{"".join("{0:08b}".format(x)+"0" for x in self.commands)}'
