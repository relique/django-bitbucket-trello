import json
import requests

from django.http import HttpResponse, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.conf import settings
from django.views.generic.edit import ProcessFormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

__all__ = ['ReceiverView']

BASE_API_URL = "https://api.trello.com/1/"
BASE_PAYLOAD = {
    'key': settings.TRELLO_KEY,
    'token': settings.TRELLO_TOKEN
}


def _extract_card_ref(string, from_branch=False):
    """Returns a card number, which is a positive integer converted into
    a string.

    If `from_branch` checks whether you are passing a commit message or
    a branch name.
    """
    if from_branch:
        lstr = string.lower()

        if lstr.startswith('card-'):
            return lstr.split('card-')[1].split('-')[0]
        elif lstr[0].isdigit():
            return lstr.split('-')[0]
    else:
        if '#' in string:
            refstr = string.split('#', 1)[1].split(' ', 1)[0]
            if refstr.isdigit():
                return refstr


def _get_card(card_ref):
    """Returns a card that is a JSON response from Trello, which is a
    result of searching.

    Since Trello API doesn't allow us to fetch card's details directly
    using card number, we do a workaround by searching for a card via
    Trello's regular search API.
    """
    payload = {
        'query': card_ref,
        'modelTypes': 'cards'
    }
    payload.update(BASE_PAYLOAD)
    url = BASE_API_URL + "search"
    r = requests.get(url, params=payload).json()

    # Now find the card that has a number match.
    for card in r['cards']:
        if str(card['idBoard']) == settings.BOARD_ID and \
                card['idShort'] == int(card_ref):
            return card


def _post_comment(card_id, text):
    payload = {
        'text': text
    }
    payload.update(BASE_PAYLOAD)
    url = BASE_API_URL + "cards/{}/actions/comments".format(card_id)
    requests.post(url, data=payload)


def _move_card(card_id, list_id):
    payload = {
        'idList': list_id,
        'pos': settings.CARD_POSITION_UPON_MOVING
    }
    payload.update(BASE_PAYLOAD)
    url = BASE_API_URL + "cards/{}".format(card_id)
    requests.put(url, data=payload)


def _get_author_name(payload):
    if 'user' in payload:
        user = payload['user']
        return user.get('display_name', user['username'])
    else:
        return payload['raw'].split(' <')[0]


def _get_actor_name(payload):
    if 'display_name' in payload:
        return payload['display_name']
    else:
        return payload['username']


class ReceiverView(ProcessFormView):
    """Main view that receives webhooks from Bitbucket and upon
    processing the data posts to Trello.
    """
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(ReceiverView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        payload = json.loads(request.body)
        hook_commits(payload)

        if 'pullrequest' in payload:
            if settings.HOOK_PULL_REQUESTS:
                hook_pull_requests(payload)

            if settings.HOOK_STAGING_BRANCH:
                hook_staging_branch(payload)

            if settings.HOOK_PRODUCTION_BRANCH:
                hook_production_branch(payload)

        return HttpResponse()


def hook_commits(data):
    """Post comments to Trello cards that are referenced through a pattern
    `#<card_number>` in a commit message.
    """
    # Check if there's any commit pushed.
    if 'push' not in data:
        return

    for chg in data['push']['changes']:
        for commit in chg['commits']:
            msg = commit['message']
            author = _get_author_name(commit['author'])
            card_ref = _extract_card_ref(msg)

            if card_ref is not None:
                card = _get_card(card_ref)
                comment = "**{} says**: {}".format(author, msg)
                _post_comment(card['id'], comment)


def hook_pull_requests(data):
    """Post comments to Trello cards that refer to newly opened pull
    requests.

    Branch name has to follow the following pattern (case insensitive):
        <card_number>-<description>
    or
        Card-<card_number>-<description>
    """
    pr = data['pullrequest']

    if str(pr['state']) == 'OPEN':
        title = pr['title']
        url = "{}pull-requests/{}".format(settings.BITBUCKET_REPO_URL,
                                          pr['id'])
        author = _get_actor_name(data['actor'])
        branch = str(pr['source']['branch']['name'])
        card_ref = _extract_card_ref(branch, from_branch=True)

        if card_ref is not None:
            card = _get_card(card_ref)
            comment = "**{} says**: {}\n\n{}".format(author, title, url)
            _post_comment(card['id'], comment)


def hook_staging_branch(data):
    """Move an existing Trello card once a pull request has been merged
    into the staging branch.
    """
    pr = data['pullrequest']

    if str(pr['state']) == 'MERGED':
        dest_branch = str(pr['destination']['branch']['name'])

        if dest_branch == settings.STAGING_BRANCH:
            branch = str(pr['source']['branch']['name'])
            card_ref = _extract_card_ref(branch, from_branch=True)

            if card_ref is not None:
                card = _get_card(card_ref)
                _move_card(card['id'], settings.STAGING_LIST_ID)


def hook_production_branch(data):
    """Move an existing Trello card once a pull request has been merged
    into the production branch.
    """
    pr = data['pullrequest']

    if str(pr['state']) == 'MERGED':
        dest_branch = str(pr['destination']['branch']['name'])

        if dest_branch == settings.PRODUCTION_BRANCH:
            branch = str(pr['source']['branch']['name'])
            card_ref = _extract_card_ref(branch, from_branch=True)

            if card_ref is not None:
                card = _get_card(card_ref)
                _move_card(card['id'], settings.PRODUCTION_LIST_ID)
