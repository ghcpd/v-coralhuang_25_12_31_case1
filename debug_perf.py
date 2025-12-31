import os
os.environ['MINIAPP_PROFILE'] = '1'
from performance_test import run

if __name__ == '__main__':
    run(1200)
