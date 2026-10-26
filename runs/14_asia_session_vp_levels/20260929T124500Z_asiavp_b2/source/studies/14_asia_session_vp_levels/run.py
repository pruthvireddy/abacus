"""Thin entry point for feature preparation or frozen study execution."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare-features',action='store_true')
    mode.add_argument('--execute',action='store_true')
    mode.add_argument('--add-sensitivities',action='store_true')
    parser.add_argument('--stage',required=True,type=Path)
    parser.add_argument('--plot-python',type=Path)
    args=parser.parse_args()
    if args.prepare_features:
        from src.preparation import prepare
        print(prepare(args.stage,args.plot_python))
    elif args.execute:
        if args.plot_python: parser.error('--plot-python is for feature preparation only')
        from src.study_run import execute
        print(execute(args.stage))
    else:
        if args.plot_python: parser.error('--plot-python is for feature preparation only')
        from src.study_run import augment_sensitivities
        print(augment_sensitivities(args.stage))


if __name__=='__main__': main()
