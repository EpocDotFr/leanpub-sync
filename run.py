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


def get_authenticity_token(session):
    debug('Getting the authenticity token')

    login_page = session.get('https://leanpub.com/login').content

    login_page_parsed = html.fromstring(login_page)

    authenticity_token = login_page_parsed.xpath('//input[@name="authenticity_token"]/@value')

    if not authenticity_token or len(authenticity_token) != 1:
        debug('Unable to find the authenticity token', err=True, terminate=True)

    authenticity_token = authenticity_token[0]

    debug('Authenticity token: ' + authenticity_token)

    return authenticity_token


def login(session, authenticity_token):
    debug('Trying to log-in')

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


def get_book_list(session):
    debug('Getting the book list')

    purchased_packages = session.get('https://leanpub.com/api/v1/purchased_packages?include=book&archived=false&type=library').json()

    books_to_download = []

    for purchased_package in purchased_packages['data']:
        book_to_download = {
            'id': purchased_package['attributes']['short_url']
        }

        book = None

        for included in purchased_packages['included']:
            if included['id'] == purchased_package['relationships']['book']['data']['id'] and included['type'] == 'books':
                book = included['attributes']

        if not book:
            debug('Book data not found for id ' + purchased_package['relationships']['book']['data']['id'], err=True)
            continue

        book_to_download['name'] = book['title']
        book_to_download['format'] = 'epub' if book['epub_available'] else 'pdf' # TODO env('PREFERED_FORMAT')

        books_to_download.append(book_to_download)

    debug('{} books to download'.format(len(books_to_download)))

    return books_to_download


def download_books(session, books_to_download):
    book_download_url = 'https://leanpub.com/s/{id}.{format}'
    output_dir = os.path.abspath(env('OUTPUT_DIR'))

    debug('Downloading books')

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

        output_file = "".join(c for c in book_to_download['name'] + '.' + book_to_download['format'] if c.isalnum() or c in (' ','.','_')).rstrip()
        output_path = os.path.join(output_dir, output_file)

        with open(output_path, 'wb') as output:
            # Display a nice progress bar while downloading the book
            with click.progressbar(length=total_length, label='Downloading to ' + output_dir) as bar:
                for chunk in book_file.iter_content(chunk_size=1024):
                    downloaded += len(chunk)

                    output.write(chunk)
                    bar.update(downloaded)


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

    authenticity_token = get_authenticity_token(session)

    # Next, we'll login usin the login endpoint (https://leanpub.com/session) with the token we scraped above along
    # your credentials.

    login(session, authenticity_token)

    # We can now get the list of books to download from the library. Fortunately, there's - at least on the library
    # page - a JSON-formatted API which simplify the process to extract them.

    books_to_download = get_book_list(session)

    # Finally, download ALL the books in the desired directory.

    download_books(session, books_to_download)


if __name__ == '__main__':
    run()
