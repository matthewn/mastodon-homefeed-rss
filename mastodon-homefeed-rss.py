#!/usr/bin/env python

import argparse
import re
import requests
import sys
import textwrap

from feedgen.feed import FeedGenerator


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
            content = f'[boosting {acct}] <br>{status["reblog"]["content"]}'
            title = status['reblog']['content'].replace('</p><p>', ' ')
            title = re.sub(
                '<[^<]+?>',
                '',
                f'[boosting {acct.split("@")[0]}] {title}',
            )
            target = status['reblog']
        else:
            acct = status['account']['acct']
            content = status['content']
            title = content.replace('</p><p>', ' ')
            title = re.sub('<[^<]+?>', '', title)
            target = status
        if target['media_attachments']:
            for item in target['media_attachments']:
                if item['type'] == 'image':
                    alt = item['description']
                    height = item['meta']['small']['height']
                    url = item['preview_url']
                    width = item['meta']['small']['width']
                    content += f'<p><img src="{url}" height="{height}" width="{width}" alt="{alt}"></p>'
        title = textwrap.shorten(title, width=80, placeholder='...')
        url = f'https://{instance}/@{acct}/{status["id"]}'
        author = status['account']['display_name']
        created = status['created_at']
        item = feed.add_entry()
        item.id(url)
        item.title(title)
        item.author({'name': author})
        item.pubDate(created)
        item.content(content)
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
        "--setup",
        action='store_true',
        help="get an access token for an instance",
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
