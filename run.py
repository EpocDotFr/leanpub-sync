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


def get_format_to_download(book, prefered_format):
    """Given a book, return the format to download taking into account the prefered one."""
    allowed_formats = ['epub', 'pdf', 'mobi']

    the_one = None

    # Check if the prefered format is available
    for allowed_format in allowed_formats:
        if allowed_format == prefered_format and allowed_format + '_available' in book and book[allowed_format + '_available']:
            the_one = allowed_format
            break

    # Prefered format not available, pick the first that's coming
    if not the_one:
        for allowed_format in allowed_formats:
            if allowed_format + '_available' in book and book[allowed_format + '_available']:
                the_one = allowed_format
                break

    return the_one


def get_authenticity_token(session):
    """Return the authenticity token."""
    debug('Getting the authenticity token')

    login_page = session.get('https://leanpub.com/login').content

    login_page_parsed = html.fromstring(login_page)

    authenticity_token = login_page_parsed.xpath('//input[@name="authenticity_token"]/@value')

    if not authenticity_token or len(authenticity_token) != 1:
        debug('Unable to find the authenticity token', err=True, terminate=True)

    authenticity_token = authenticity_token[0]

    debug('Authenticity token: ' + authenticity_token)

    return authenticity_token


def login(session, authenticity_token, email, password):
    """Log in to Leanpub."""
    debug('Trying to log-in')

    login_data = {
        'utf8': '✓',
        'session[email]': email,
        'session[password]': password,
        'authenticity_token': authenticity_token
    }

    login_result = session.post('https://leanpub.com/session', data=login_data)

    try:
        login_result.raise_for_status() # If login failed, our script will fail too
    except Exception as e:
        debug('Error while logging in: {}'.format(e), err=True, terminate=True)

    debug('Logged in successfully')


def get_book_list(session):
    """Return a list of books."""
    debug('Getting the book list')

    purchased_packages = session.get('https://leanpub.com/api/v1/purchased_packages?include=book&archived=false&type=library').json()

    books_to_download = []

    for purchased_package in purchased_packages['data']:
        book_to_download = {
            'id': purchased_package['attributes']['short_url']
        }

        book = None

        for included in purchased_packages['included']: # Get the book data
            if included['id'] == purchased_package['relationships']['book']['data']['id'] and included['type'] == 'Book':
                book = included['attributes']

        if not book:
            debug('Book not found for id #' + purchased_package['relationships']['book']['data']['id'], err=True)
            continue

        book_to_download['name'] = book['title']
        book_to_download['format'] = get_format_to_download(book, env('PREFERED_FORMAT'))

        books_to_download.append(book_to_download)

    debug('{} books to download'.format(len(books_to_download)))

    return books_to_download


def download_books(session, books_to_download, output_dir):
    """Download a list of books."""
    book_download_url = 'https://leanpub.com/s/{id}.{format}'
    output_dir = os.path.abspath(output_dir)

    if not os.path.isdir(output_dir):
        debug(output_dir + ' is not a directory or does not exists.', err=True, terminate=True)

    debug('Downloading books')

    for book_to_download in books_to_download:
        book_file = session.get(book_download_url.format(id=book_to_download['id'], format=book_to_download['format']), stream=True)

        try:
            book_file.raise_for_status()
        except Exception as e:
            debug('Error while downloading this book: {}'.format(e), err=True)
            continue

        total_length = int(book_file.headers['Content-Length'])

        # Remove unallowed characters in the filename
        output_file = "".join(c for c in book_to_download['name'] + '.' + book_to_download['format'] if c.isalnum() or c in (' ','.','_')).rstrip()
        output_path = os.path.join(output_dir, output_file)

        with open(output_path, 'wb') as output:
            # Display a nice progress bar while downloading the book
            with click.progressbar(length=total_length, label=book_to_download['name']) as bar:
                for chunk in book_file.iter_content(chunk_size=1024):
                    output.write(chunk)
                    bar.update(len(chunk))

    debug('Done!')


def run():
    """Run the script."""
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

    # Next, we'll post a forged form to the login endpoint (https://leanpub.com/session) with the token we scraped
    # above along Leanpub credentials.

    login(session, authenticity_token, env('LEANPUB_EMAIL'), env('LEANPUB_PASSWORD'))

    # We can now get the list of books to download from the library. Fortunately, there's - at least on the library
    # page - a JSON-formatted API which simplify the process to extract them.

    books_to_download = get_book_list(session)

    # Finally, download ALL the books in the desired directory.

    download_books(session, books_to_download, env('OUTPUT_DIR'))


if __name__ == '__main__':
    run()
