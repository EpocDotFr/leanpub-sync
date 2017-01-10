from envparse import env, Env
import logging
import os


def debug(message, err=False, terminate=False):
    """Log a regular or error message to the standard output, optionally terminating the script."""
    logging.getLogger().log(logging.ERROR if err else logging.INFO, message)

    if terminate:
		sys.exit(1)


def run():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        stream=sys.stdout
    )

	logging.getLogger().setLevel(logging.INFO)



if __name__ == '__main__':
	run()