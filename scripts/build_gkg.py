import argparse
import logging
import os
import sys


def main(args):

    logging.basicConfig(
        filename="/tmp/build_gkg.log",
        level=logging.DEBUG,
        format="%(asctime)s, %(name)s, %(levelname)s, %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        force=True,
    )

    log = logging.getLogger("gkg")
    if args.verbose:
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        log.addHandler(h)

    log.info("starting build_gkg")

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from sigmal.gkg import GenomeKG

    gkg = GenomeKG()
    log.info("creating GenomeKG from %s" % (args.input_dir))
    gkg.create(args.input_dir)
    log.info("OK: GenomeKG created.")
    if args.compute_tree:
        log.info(
            "computing BallTree.. using distance metric %s" % (args.distance_metric)
        )
        gkg.compute_tree(metric=args.distance_metric)
        log.info("OK: BallTree computed.")
    log.info("saving GenomeKG..")
    r = gkg.save(args.output_file)
    log.info("OK: GenomeKG save to %s" % (r))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", default=False, action="store_true")
    ap.add_argument(
        "-c",
        "--compute_tree",
        default=True,
        action="store_true",
        help="Compute balltree.",
    )
    ap.add_argument(
        "--distance_metric",
        default="minkowski",
        action="store_true",
        help="Distance metric for compute balltree.",
    )
    ap.add_argument(
        "-o",
        "--output_file",
        default=None,
        help="Optional output GenomeKG file path. Defaults to {input_dir}.gkg.",
    )

    ap.add_argument("input_dir")

    args = ap.parse_args()

    exit(main(args))
