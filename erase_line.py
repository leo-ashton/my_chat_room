CURSOR_UP_ONE = '\x1b[1A'
ERASE_LINE = '\x1b[2K'

import sys
sys.stdout.write(CURSOR_UP_ONE)
print("Hello!")
sys.stdout.write(ERASE_LINE)
sys.stdout.write(ERASE_LINE)