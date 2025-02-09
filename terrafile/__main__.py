import os
import sys
import argparse

from terrafile import update_modules

optimizedownloads = False
if len(sys.argv) < 3:
    if len(sys.argv) < 2:
        path = os.getcwd()
    else:
        path = sys.argv[1]
else:
    parser = argparse.ArgumentParser()
    parser.add_argument('--terrafile', required=False, default=os.getcwd(), dest='path', help='location of Terrafile')
    parser.add_argument('--optimizedownloads', required=False, default=False, dest='optimizedownloads', help='Switch on opinionated distinct module downloads')
    args = parser.parse_args()
    path = args.path
    optimizedownloads = args.optimizedownloads


update_modules(path, optimizedownloads)
