import sys


def main():
    print(100)
    try:
        raise Exception('test')
    except Exception as __comPYned_tmp:
        print('Caught %s: %s' % (type(__comPYned_tmp).__name__, __comPYned_tmp), file=sys.stderr)
if __name__ == '__main__':
    main()


