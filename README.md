# mastodon-homefeed-rss
This is a Python script that generates an RSS feed from a Mastodon user's home feed.

It is a quick, dirty, and probably naive hack. But it is working, and when it breaks, I intend to fix it (unless a better alternative comes along). _"This is the way."_

For more on why this script exists, see [my blog post about it](https://www.mahnamahna.net/blog/announcing-mastodon-homefeed-rss/).

To make effective use of this script you will likely need a Linux machine where you can:
  - run a script with Python 3.8 or later, and
  - write a file to a web-accessible directory, and
  - set up a cron job

Sure, it is also possible to run this on a Windows or Mac machine and send the generated XML file somewhere, but if you are already thinking along those lines, you sound like you're smart enough to figure out those details. I'll tell you how I use this thing.

1. `git clone` the code to where it's gonna live.
2. Create a Python virtual environment, populate it, and activate it.
  - If you are a `poetry` user, you can do `poetry install; poetry shell`.
  - Otherwise `python -m venv .venv; source .venv/bin/activate` followed by `pip install -r requirements.txt` should do it.
3. Run `./mastodon-homefeed-rss.py --setup <instance>` where _instance_ is the domain of your home Mastodon server (e.g. mastodon.social). The script will have you visit a page at your Mastodon instance that will allow you to grant the script access to your home feed. At that page, you will receive an authorization code. Paste that code in when the script prompts you, and hit Enter. The script will respond with your access token.
4. You can now generate an (Atom-flavored) RSS feed by doing `./mastodon-homefeed-rss.py --token <token> <instance>` where _token_ is that access token you received in the previous step. A file named _mastodon-homefeed.xml_ will be created in the current directory.
5. If you'd like the output file to go elsewhere, you can do this: `./mastodon-homefeed-rss.py --token <token> --output_file /path/to/feed.xml <instance>`
6. Now hook yourself up with a cron job that runs the script with the options you need at the interval you desire.

Oh yeah, one additional wrinkle, back at step 3. If the access token you receive starts with a dash/hyphen character, that's not gonna work due to a bug in Python's argparse module that is [not going to be fixed](https://github.com/python/cpython/issues/53580) (!). So in this case, just do step 3 again to get a different token.

Please open an issue on GitHub if you run into trouble. Or if you run into trouble and know how to fix it, delight me with a pull request! Cheers.
