import re
from subprocess import check_output


def main():
    with open('expected.txt', 'r') as f:
        expected = f.read()

    go_output = check_output(['go', 'run', 'test_select.go'])

    pattern = re.compile(expected, re.X)

    if pattern.fullmatch(go_output.decode()) is not None:
        print('Go tests match the expected output')
    else:
        raise Exception('Go tests DO NOT match the expected output')


if __name__ == '__main__':
    main()
