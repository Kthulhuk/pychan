import time
import unittest
from io import BytesIO
import re

from chan import Chan, select, go


py_output = BytesIO()

with open('tests/expected.txt', 'r') as f:
    expected = f.read()

pattern = re.compile(expected, re.X)


def py_match():
    if pattern.fullmatch(py_output.getvalue().decode()) is not None:
        return True
    else:
        return False


def read():
    """The select should block,
    Then, the <- ch1 case should be executed very soon after
    the other goroutine times out.
    Expected output :
    -----------------
    Writing 42 to ch1
    Waited 1.00[0-9]*s
    """

    ch1 = Chan()

    def write_channel_delayed():
        """Write an int nb into a channel ch with a delay of 1 second"""
        time.sleep(1)
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    go(write_channel_delayed)

    start = time.time()
    chan, nb = select(consumers=[ch1], producers=[])
    if chan == ch1:
        py_output.write('Waited {}\n'.format(time.time() - start).encode())


def read_default():
    """The select should execute the default code as many times as needed
    (hopefully once)
    Then the <-ch1 case should happen
    Expected output :
    -----------------
    Selected default behavior
    Writing 42 to ch1
    Received number 42 from ch1 after 1[0-9].[0-9]*µs
    """

    ch1 = Chan()
    ch2 = Chan()

    def write_channel(ch):
        """Wait for ch to be readable and Write an int nb
        into a channel ch"""
        ch.get()
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    go(write_channel,  ch2)

    from_ch1 = 0
    wrote_to_ch2 = False
    start = time.time()
    while from_ch1 == 0:
        chan, nb = select(consumers=[ch1], producers=[],
                          default=True)
        if chan == ch1:
            elapsed = time.time() - start
            from_ch1 = nb
            py_output.write('Received number '
                            '{} from ch1 after '
                            '{}\n'.format(from_ch1, elapsed).encode())
        if chan is 'default':
            py_output.write('Selected default behavior\n'.encode())
            if not wrote_to_ch2:
                ch2.put(1)
                wrote_to_ch2 = True


def read_read_default():
    """Two channels can be read and there's a default clause
    Expected output :
    -----------------
    Writing (42|51) to ch(1|2)
    Writing (42|51) to ch(1|2)
    Received number (42|51) from ch(1|2)
    """

    ch1 = Chan()
    ch2 = Chan()

    def write_channel1():
        """Write 42 into ch1"""
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    def write_channel2():
        """Write 51 into ch2"""
        py_output.write('Writing 51 to ch2\n'.encode())
        ch2.put(51)

    go(write_channel1)
    go(write_channel2)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    chan, nb = select(consumers=[ch1, ch2], producers=[],
                      default=True)
    if chan == ch1:
        py_output.write('Received number {} from ch1\n'.format(nb).encode())
    elif chan == ch2:
        py_output.write('Received number {} from ch2\n'.format(nb).encode())
    elif chan == 'default':
        raise Exception('Selected default behavior')

    if nb == 42:  # ch1.get() happened
        assert ch2.get() == 51, "We should be able to read '51' from ch2"
    elif nb == 51:  # ch2.get() happened
        assert ch1.get() == 42, "We should be able to read '42' from ch1"
    else:
        raise Exception('WTF ?')


def read_read():
    """Two channels can be read and no default clause
    Expected output :
    -----------------
    Writing (42|51) to ch(1|2)
    Writing (42|51) to ch(1|2)
    Received number (42|51) from ch(1|2)
    """

    ch1 = Chan()
    ch2 = Chan()

    def write_channel1():
        """Write 42 into ch1"""
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    def write_channel2():
        """Write 51 into ch2"""
        py_output.write('Writing 51 to ch2\n'.encode())
        ch2.put(51)

    go(write_channel1)
    go(write_channel2)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    chan, nb = select(consumers=[ch1, ch2], producers=[])
    if chan == ch1:
        py_output.write('Received number {} from ch1\n'.format(nb).encode())
    elif chan == ch2:
        py_output.write('Received number {} from ch2\n'.format(nb).encode())

    if nb == 42:  # ch1.get() happened
        assert ch2.get() == 51, "We should be able to read '51' from ch2"
    elif nb == 51:  # ch2.get() happened
        assert ch1.get() == 42, "We should be able to read '42' from ch1"
    else:
        raise Exception('WTF ?')


def read_write_default():
    """One channel can be read, the written and there's a default clause
    Expected output :
    -----------------
    (Writing 42 to ch1|Reading from ch2)
    (Writing 42 to ch1|Reading from ch2)
    (Received number 42 from ch1|Sent number 51 to ch2)
    """

    ch1 = Chan()
    ch2 = Chan()

    def write_channel():
        """Write 42 into ch1"""
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    def read_channel():
        """Read the value in ch2 and write it in ch1"""
        py_output.write('Reading from ch2\n'.encode())
        x = ch2.get()
        ch1.put(x)

    go(write_channel)
    go(read_channel)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    nb = 51

    chan, nb = select(consumers=[ch1], producers=[(ch2, 51)],
                      default=True)
    if chan == ch1:
        py_output.write('Received number {} from ch1\n'.format(nb).encode())
    elif chan == ch2:
        py_output.write('Sent number 51 to ch2\n'.encode())
    elif chan == 'default':
        raise Exception('Selected default behavior')

    if nb == 42:  # ch1.get() happened
        ch2.put(17)
        assert ch1.get() == 17, "We should be able to read 17 from ch1"
    elif nb is None:  # ch2.put(51) happened
        assert ch1.get() == 42, "We should be able to read '42' from ch1"
    else:
        raise Exception('WTF ?')


def read_write():
    """One channel can be read, the written and there's a default clause
    Expected output :
    -----------------
    (Writing 42 to ch1|Reading from ch2)
    (Writing 42 to ch1|Reading from ch2)
    (Received number 42 from ch1|Sent number 51 to ch2)
    """

    ch1 = Chan()
    ch2 = Chan()

    def write_channel():
        """Write 42 into ch1"""
        py_output.write('Writing 42 to ch1\n'.encode())
        ch1.put(42)

    def read_channel():
        """Read the value in ch2 and write it in ch1"""
        py_output.write('Reading from ch2\n'.encode())
        x = ch2.get()
        ch1.put(x)

    go(write_channel)
    go(read_channel)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    nb = 51

    chan, nb = select(consumers=[ch1], producers=[(ch2, 51)])
    if chan == ch1:
        py_output.write('Received number {} from ch1\n'.format(nb).encode())
    elif chan == ch2:
        py_output.write('Sent number 51 to ch2\n'.encode())

    if nb == 42:  # ch1.get() happened
        ch2.put(17)
        assert ch1.get() == 17, "We should be able to read 17 from ch1"
    elif nb is None:  # ch2.put(51) happened
        assert ch1.get() == 42, "We should be able to read '42' from ch1"
    else:
        raise Exception('WTF ?')


def write_write_default():
    """Two channels can be read and there's a default clause
    Expected output :
    -----------------
    Writing (42|51) to ch(1|2)
    Writing (42|51) to ch(1|2)
    Received number (42|51) from ch(1|2)
    """

    ch1A = Chan()
    ch1B = Chan()
    ch2A = Chan()
    ch2B = Chan()

    def read_channel1():
        """Read the value in ch1A and write it in ch1B"""
        py_output.write('Reading from ch1\n'.encode())
        x = ch1A.get()
        ch1B.put(x)

    def read_channel2():
        """Read the value in ch2A and write it in ch2B"""
        py_output.write('Reading from ch2\n'.encode())
        x = ch2A.get()
        ch2B.put(x)

    go(read_channel1)
    go(read_channel2)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    nb1 = 42
    nb2 = 51
    sent = 0

    chan, nb = select(consumers=[], producers=[(ch1A, 42), (ch2A, 51)],
                      default=True)
    if chan == ch1A:
        py_output.write('Sent number 42 to ch2\n'.encode())
        sent = nb1
    elif chan == ch2A:
        py_output.write('Sent number 51 to ch2\n'.encode())
        sent = nb2
    elif chan == 'default':
        raise Exception('Selected default behavior')

    if sent == 42:  # ch1.put(42) happened
        ch2A.put(17)
        assert ch1B.get() == 42, "We should be able to read 42 from ch1B"
    elif sent == 51:  # ch2.put(51) happened
        ch1A.put(17)
        assert ch2B.get() == 51, "We should be able to read 51 from ch2B"
    else:
        raise Exception('WTF ?')


def write_write():
    """Two channels can be read and there's a default clause
    Expected output :
    -----------------
    Writing (42|51) to ch(1|2)
    Writing (42|51) to ch(1|2)
    Received number (42|51) from ch(1|2)
    """

    ch1A = Chan()
    ch1B = Chan()
    ch2A = Chan()
    ch2B = Chan()

    def read_channel1():
        """Read the value in ch1A and write it in ch1B"""
        py_output.write('Reading from ch1\n'.encode())
        x = ch1A.get()
        ch1B.put(x)

    def read_channel2():
        """Read the value in ch2A and write it in ch2B"""
        py_output.write('Reading from ch2\n'.encode())
        x = ch2A.get()
        ch2B.put(x)

    go(read_channel1)
    go(read_channel2)

    time.sleep(0.1)
    # Hopefully this is enough time to let
    # the other two goroutines block on their channel writes

    nb1 = 42
    nb2 = 51
    sent = 0

    chan, nb = select(consumers=[], producers=[(ch1A, 42), (ch2A, 51)])
    if chan == ch1A:
        py_output.write('Sent number 42 to ch2\n'.encode())
        sent = nb1
    elif chan == ch2A:
        py_output.write('Sent number 51 to ch2\n'.encode())
        sent = nb2

    if sent == 42:  # ch1.put(42) happened
        ch2A.put(17)
        assert ch1B.get() == 42, "We should be able to read 42 from ch1B"
    elif sent == 51:  # ch2.put(51) happened
        ch1A.put(17)
        assert ch2B.get() == 51, "We should be able to read 51 from ch2B"
    else:
        raise Exception('WTF ?')


class ChanTests(unittest.TestCase):
    def test_select_py(self):

        tests = [read, read_default,
                 read_read, read_read_default,
                 read_write, read_write_default,
                 write_write, write_write_default]

        for f in tests:
            name = f.__name__
            py_output.write('>>> Starting test {} <<<\n'.format(name).encode())
            f()
            py_output.write('>>> Test {} over <<<\n\n'.format(name).encode())

        self.assertTrue(py_match())


if __name__ == '__main__':
    unittest.main()
