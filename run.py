from envparse import env, Env
from lxml import html
import requests
import logging
import sys


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

    Env.read_envfile('.env')

    # Firstly, we'll get the token called "authenticity_token" on the login page (https://leanpub.com/login),
    # stored in a hidden input. This token - which is always different - is required when submitting the login form.

    logging.info('Getting the authenticity token')

    login_page = requests.get('https://leanpub.com/login').content

    login_page_parsed = html.fromstring(login_page)

    authenticity_token = login_page_parsed.xpath('//input[@name="authenticity_token"]/@value')[0]

    logging.info('Authenticity token: ' + authenticity_token)

    # Next, we'll forge the data to be sent to the login endpoint (https://leanpub.com/session) using the token we
    # scraped above, along your credentials.

    login_data = {
        'utf8': '✓',
        'session[email]': env('LEANPUB_EMAIL'),
        'session[password]': env('LEANPUB_PASSWORD'),
        'authenticity_token': authenticity_token
    }

    login_result = requests.post('https://leanpub.com/session', data=login_data)

    login_result.raise_for_status()

    logging.info('Logged in successfully')

    # We are now ready to get the list of books to download from the library. Fortunately, there's - at least on the
    # library page - a JSON-formatted API which simplify the process to extract them.

    logging.info('Getting books to download')

    purchased_packages = requests.get('https://leanpub.com/api/v1/purchased_packages?include=book').json

    # https://leanpub.com/api/v1/purchased_packages?include=book%2C%20book.accepted_authors&archived=false&page=1&sort=created_at_desc&type=library&user_id=223538

if __name__ == '__main__':
    run()