import base64

from twisted.internet import defer
from twisted.words.xish import domish
from txmongo import gridfs

from base import send_raw
import bnw_core.base
import bnw_core.bnw_mongo
from bnw_core import bnw_objects as objs


def get_avatar(iq):
    mimetype = str(iq.vCard.PHOTO.TYPE)
    if mimetype not in ('image/png', 'image/jpeg', 'image/gif'):
        return
    filedata = iq.vCard.PHOTO.BINVAL
    if not filedata:
        return
    filedata = str(filedata)
    if len(filedata) > 32768:
        # XEP-0153 says 8KB (4*8KB for Base64).
        return
    try:
        decoded = base64.b64decode(filedata) # TODO: deferToThread
    except TypeError:
        return
    else:
        return mimetype, decoded

@defer.inlineCallbacks
def vcard(iq, iq_user):
    if not iq.vCard:
        defer.returnValue(False)
    if not iq_user:
        # User which have been sent IQ not registered.
        defer.returnValue(True)
    if iq.vCard.PHOTO:
        av = get_avatar(iq)
        if av:
            mimetype, decoded = av
            fs = yield bnw_core.bnw_mongo.get_fs('avatars')
            extension = mimetype.split('/')[1]
            avid = fs.put(
                decoded, filename=iq_user['name']+'.'+extension,
                contentType=mimetype)
            if iq_user.get('avatar', None):
                fs.delete(iq_user['avatar'][0])
            _ = yield objs.User.mupdate(
                {'name': iq_user['name']},
                {'$set': {'avatar': [avid,mimetype]}})
    defer.returnValue(True)

VERSION_XMLNS = 'jabber:iq:version'
def version(iq, iq_user):
    if iq.query and iq.query.uri == VERSION_XMLNS:
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id'):
            reply['id'] = iq['id']
        reply.addElement('query', VERSION_XMLNS)
        reply.query.addElement('name', content='BnW')
        reply.query.addElement('version', content='0.1')
        reply.query.addElement('os', content='OS/360')
        send_raw(iq['from'], iq['to'], reply)
        return True

DISCO_ITEMS_XMLNS = 'http://jabber.org/protocol/disco#items'
def disco_items(iq, iq_user):
    if iq.query and iq.query.uri == DISCO_ITEMS_XMLNS:
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id'):
            reply['id'] = iq['id']
        reply.addElement('query', DISCO_ITEMS_XMLNS)
        send_raw(iq['from'], iq['to'], reply)
        return True

DISCO_INFO_XMLNS = 'http://jabber.org/protocol/disco#info'
FEATURES = ('jabber:iq:version',
            'http://jabber.org/protocol/chatstates',
            'http://jabber.org/protocol/disco#info',
            'http://jabber.org/protocol/disco#items',
            'urn:xmpp:receipts',
)
def disco_info(iq, iq_user):
    if iq.query and iq.query.uri == DISCO_INFO_XMLNS:
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id'):
            reply['id'] = iq['id']
        reply.addElement('query', DISCO_INFO_XMLNS)
        reply.query.addElement('identity')
        reply.query.identity['category'] = 'client' # not pretty sure
        reply.query.identity['type'] = 'bot'
        reply.query.identity['name'] = 'BnW'

        for feature_name in FEATURES:
            feature = reply.query.addElement('feature')
            feature['var'] = feature_name
    
        send_raw(iq['from'], iq['to'], reply)
        return True

handlers = [
    vcard,
    version,
    disco_items,
    disco_info,
]
