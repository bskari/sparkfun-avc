def dead_frequency(frequency):
    """Returns an approprtiate dead signal frequency for the given
    signal.
    """
    if frequency < 38:
        return 49.890
    return 26.995


def format_command(
    frequency,
    useconds
):
    """Returns the JSON command string for this command tuple."""
    dead = dead_frequency(frequency)
    return {
        'frequency': frequency,
        'dead_frequency': dead,
        'burst_us': useconds,
        'spacing_us': useconds,
        'repeats': 1,
    }


def to_bit(number):
    """0 => 0, anything else => 1."""
    if number > 0:
        return 1
    return 0


def ones_count(number):
    """Returns the number of 1s in the binary representation of the
    number.
    """
    mask = 1
    ones = 0
    while mask <= number:
        ones += to_bit(mask & number)
        mask <<= 1
    return ones


def command(throttle, turn):
    """Returns a JSON formatted control command for the Dune Warrior."""
    assert throttle >= 0 and throttle < 32
    # Turning too sharply causes the servo to push harder than it can
    # go, so limit this
    assert turn >= 8 and turn < 58

    frequency = 27.145
    even_parity_bit = to_bit(
        (
            ones_count(throttle)
            + ones_count(turn)
            + 3
        ) % 2
    )

    bit_pattern = (
        to_bit(turn & 0x8),
        to_bit(turn & 0x4),
        to_bit(turn & 0x2),
        to_bit(turn & 0x1),
        0,
        0,
        to_bit(turn & 0x20),
        to_bit(turn & 0x10),
        to_bit(throttle & 0x10),
        to_bit(throttle & 0x8),
        to_bit(throttle & 0x4),
        to_bit(throttle & 0x2),
        to_bit(throttle & 0x1),
        1,
        1,
        1,
        0,
        0,
        even_parity_bit,
        0,
        0,
        0
    )
    assert(len(bit_pattern) == 22)
    assert(sum(bit_pattern) % 2 == 0)

    command = [format_command(frequency, 500)]
    total_useconds = 0
    for bit in bit_pattern[:-1]:
        if bit == 0:
            useconds = 127
        else:
            useconds = 200
        command.append(format_command(27.145, useconds))
        total_useconds += useconds

    if bit_pattern[-1] == 0:
        useconds = 127
    else:
        useconds = 200
    total_useconds += useconds
    command.append({
        'frequency': frequency,
        'dead_frequency': dead_frequency(frequency),
        'burst_us': useconds,
        'spacing_us': 7000 - total_useconds,
        'repeats': 1,
    })

    return command
