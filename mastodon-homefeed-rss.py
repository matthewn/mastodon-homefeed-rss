#!/usr/bin/env python

import argparse
import re
import requests
import sys

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


def get_authorization_page(instance, client_id):
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


def generate_feed(instance, access_token, output_file='mastodon-homefeed.xml'):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(
        f'https://{instance}/api/v1/timelines/home',
        headers=headers,
    )

    if response.status_code != 200:
        print(f'Error received from instance: {response.json()["error"]}')
        sys.exit(1)

    if statuses := response.json():
        feed = FeedGenerator()
        feed.id('https://mahnamahna.net/gen/mastodon-homefeed.xml')
        feed.title('mastodon home feed')
        for status in statuses:
            if status['reblog']:
                acct = status['reblog']['account']['acct']
                url = f'https://{instance}/@{acct}/{status["id"]}'
                content = f'[boosting {acct.split("@")[0]}] <br>{status["reblog"]["content"]}'
            else:
                acct = status['account']['acct']
                url = f'https://{instance}/@{acct}/{status["id"]}'
                content = status['content']
            author = status['account']['display_name']
            datetime = status['created_at']
            title = re.sub('<[^<]+?>', '', content[:80])
            item = feed.add_entry()
            item.id(url)
            item.title(title)
            item.author({'name': author})
            item.pubDate(datetime)
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
        help='pathname for file output (./mastodon-homefeed.xml if omitted)',
    )
    args = parser.parse_args()
    instance = str(args.instance)

    if not args.setup:

        # generate a feed
        if args.output_file:
            generate_feed(instance, str(args.token), str(args.output_file))
        else:
            generate_feed(instance, str(args.token))

    else:

        # do the setup routine
        (client_id, client_secret) = get_client_id_and_secret(instance)
        url = get_authorization_page(instance, client_id)
        print('Please visit the following URL:\n')
        print(f'{url}\n')
        user_authz_code = input(
            'Paste in the authorization code provided at the URL above: '
        )
        access_token = get_access_token(
            instance, client_id, client_secret, user_authz_code
        )
        print(f'\nYour access token is: {access_token}')