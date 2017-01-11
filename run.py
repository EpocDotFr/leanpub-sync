from envparse import env, Env
from lxml import html
import requests
import logging
import sys
import click
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

    Env.read_envfile('.env')

    session = requests.Session() # To reuse the Leanpub cookies across all requests

    # Firstly, we'll get the token called "authenticity_token" on the login page (https://leanpub.com/login),
    # stored in a hidden input. This token - which is always different - is required when submitting the login form.

    debug('Getting the authenticity token')

    login_page = session.get('https://leanpub.com/login').content

    login_page_parsed = html.fromstring(login_page)

    authenticity_token = login_page_parsed.xpath('//input[@name="authenticity_token"]/@value')

    if len(authenticity_token) != 1:
        debug('Unable to find the authenticity token', err=True, terminate=True)

    authenticity_token = authenticity_token[0]

    debug('Authenticity token: ' + authenticity_token)

    # Next, we'll forge the data to be sent to the login endpoint (https://leanpub.com/session) using the token we
    # scraped above, along your credentials.

    login_data = {
        'utf8': '✓',
        'session[email]': env('LEANPUB_EMAIL'),
        'session[password]': env('LEANPUB_PASSWORD'),
        'authenticity_token': authenticity_token
    }

    login_result = session.post('https://leanpub.com/session', data=login_data)

    try:
        login_result.raise_for_status() # If login failed, our script will fail too
    except Exception as e:
        debug('Error while logging in: {}'.format(e), err=True, terminate=True)

    debug('Logged in successfully')

    # We can now get the list of books to download from the library. Fortunately, there's - at least on the library
    # page - a JSON-formatted API which simplify the process to extract them.

    debug('Getting the book list')

    purchased_packages = session.get('https://leanpub.com/api/v1/purchased_packages?include=book&archived=false&type=library').json()

    books_to_download = []

    for purchased_package in purchased_packages['data']:
        book_to_download = {
            'id': purchased_package['attributes']['short_url']
        }

        book = next(b for b in purchased_packages['included'] if b['id'] == purchased_package['relationships']['book']['data']['id'])

        book_to_download['name'] = book['attributes']['title']
        book_to_download['format'] = 'epub' if book['attributes']['epub_available'] else 'pdf' # TODO env('PREFERED_FORMAT')

        books_to_download.append(book_to_download)

    debug('{} books to download'.format(len(books_to_download)))

    # Finally, download ALL the books.

    debug('Downloading books')

    book_download_url = 'https://leanpub.com/s/{id}.{format}'

    for book_to_download in books_to_download:
        debug('  ' + book_to_download['name'])

        book_file = session.get(book_download_url.format(id=book_to_download['id'], format=book_to_download['format']), stream=True)

        try:
            book_file.raise_for_status()
        except Exception as e:
            debug('Error while downloading this book: {}'.format(e), err=True)
            continue

        total_length = int(book_file.headers['Content-Length'])
        downloaded = 0

        output_file = os.path.abspath(os.path.join(env('OUTPUT_DIR'), book_to_download['name'] + '.' + book_to_download['format']))

        with open(output_file, 'wb') as output:
            with click.progressbar(length=total_length) as bar:
                for chunk in book_file.iter_content(chunk_size=1024):
                    downloaded += len(chunk)

                    output.write(chunk)

                    bar.update(downloaded)


if __name__ == '__main__':
    run()