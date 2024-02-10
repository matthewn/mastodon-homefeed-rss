#!/usr/bin/env python

import argparse
import re
import requests
import sys
import textwrap
import unicodedata

from feedgen.feed import FeedGenerator


def remove_control_characters(s):
    # taken from https://stackoverflow.com/a/19016117
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")


def get_client_id_and_secret(instance):
    data = {
        'client_name': 'mastodon-homefeed-rss',
        'redirect_uris': 'urn:ietf:wg:oauth:2.0:oob',
        'scopes': 'read',
        'website': 'https://mahnamahna.net/mastodon-homefeed-rss',
    }
    response = requests.post(f'https://{instance}/api/v1/apps', data=data)
    client_id = response.json()['client_id']
    client_secret = response.json()['client_secret']
    return client_id, client_secret


def get_authorization_page_url(instance, client_id):
    return f'https://{instance}/oauth/authorize?client_id={client_id}&scope=read&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code'


def get_access_token(instance, client_id, client_secret, user_authz_code):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code',
        'code': user_authz_code,
        'scope': 'read',
    }
    response = requests.post(f'https://{instance}/oauth/token', data=data)
    access_token = response.json()['access_token']
    return access_token


def strip_title(title):
    title = title.replace('</p><p>', ' ')
    title = re.sub(r'<br ?/?>', ' ', title)
    title = re.sub('<[^<]+?>', '', title)
    return title


def generate_feed(instance, access_token, output_file):
    if output_file is None:
        output_file = 'mastodon-homefeed.xml'

    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(
        f'https://{instance}/api/v1/timelines/home',
        headers=headers,
    )

    if response.status_code != 200:
        try:
            print(f'Error received from instance: {response.json()["error"]}')
        except requests.exceptions.JSONDecodeError:
            print(f'Error received from instance. HTTP status code: {response.status_code}')
        sys.exit(1)

    feed = FeedGenerator()
    feed.id('https://mahnamahna.net/mastodon-homefeed-rss')
    feed.title('mastodon home feed')
    statuses = response.json()
    for status in statuses:
        if status['reblog']:
            acct = status['reblog']['account']['acct']
            status_id = status['reblog']['id']
            content = f'[boosting {acct}] <br>{status["reblog"]["content"]}'
            title = strip_title(
                f'[{acct.split("@")[0]}] {status["reblog"]["content"]}'
            )
            target = status['reblog']
        else:
            acct = status['account']['acct']
            status_id = status['id']
            content = status['content']
            title = strip_title(content)
            target = status
        if target['media_attachments']:
            for item in target['media_attachments']:
                description = item['description']
                height = width = ''
                if item.get('meta'):
                    if item['meta'].get('small'):
                        height = item['meta']['small']['height']
                        width = item['meta']['small']['width']
                if item['type'] == 'image':
                    url = item['preview_url']
                    content += f'<p><img src="{url}" height="{height}" width="{width}" alt="{description}" title="{description}"></p>'
                if item['type'] == 'gifv':
                    url = item['url']
                    content += f'<video title="{description}" role="application" src="{url}" autoplay="" playsinline="" loop="" height="{height}" width="{width}"></video>'
                if item['type'] == 'video':
                    url = item['url']
                    poster = item['preview_url']
                    content += f'<video title="{description}" controls role="button" preload="none" src="{url}" poster="{poster}" tabindex="0" height="{height}" width="{width}"></video>'
        if target['poll']:
            content += (
                '<ul><li>'
                + '<li>'.join([d['title'] for d in target['poll']['options']])
                + '</ul>'
            )
        title = textwrap.shorten(title, width=80, placeholder='...')
        if title == '':
            title = '(no title)'
        url = f'https://{instance}/@{acct}/{status_id}'
        author = status['account']['display_name']
        created = status['created_at']
        item = feed.add_entry()
        item.id(url)
        item.title(title)
        item.author({'name': author})
        item.pubDate(created)
        item.content(remove_control_characters(content))
        item.link({'href': url})
    feed.atom_file(output_file)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument(
        'instance',
        help='the domain name of your instance, e.g. mastodon.social',
    )
    mode.add_argument(
        '--setup',
        action='store_true',
        help='get an access token for an instance',
    )
    mode.add_argument(
        '--token',
        help='generate feed for given access token',
    )
    parser.add_argument(
        '--output_file',
        help='pathname for file output (mastodon-homefeed.xml if omitted)',
    )
    args = parser.parse_args()
    instance = args.instance

    if args.token:
        generate_feed(instance, args.token, args.output_file)

    else:
        # do the setup routine
        (client_id, client_secret) = get_client_id_and_secret(instance)
        url = get_authorization_page_url(instance, client_id)
        print('Please visit the following page:\n')
        print(f'{url}\n')
        user_authz_code = input(
            'Paste in the authorization code provided at the page linked above: '
        )
        access_token = get_access_token(
            instance, client_id, client_secret, user_authz_code
        )
        print(f'\nYour access token is: {access_token}')
