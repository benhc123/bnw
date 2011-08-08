# -*- coding: utf-8 -*-
from twisted.words.xish import domish

from base import *
import random
from twisted.internet import defer
import base64
from txmongo import gridfs
import bnw_core.base
from bnw_core import bnw_objects as objs

@defer.inlineCallbacks
def vcard_getav(iq,iq_user):
    if iq.vCard and iq.vCard.PHOTO:
        if not iq_user:
            defer.returnValue( True )
        mimetype = str(iq.vCard.PHOTO.TYPE)
        if not (mimetype in ('image/png','image/jpeg','image/gif')):
            defer.returnValue( True )
        filedata = iq.vCard.PHOTO.BINVAL
        if not filedata:
            defer.returnValue( True )
        filedata = str(filedata)
        if len(filedata)>32768*2: # xep-0153 says 8KB
            defer.returnValue( True )
        try:
            decoded = base64.b64decode(filedata) # TODO: deferToThread
        except TypeError:
            defer.returnValue( True )
        if len(decoded)>32768: # check decoded size
            defer.returnValue( True )
        fs = yield bnw_core.base.get_fs('avatars')
        extension = mimetype.split('/')[1]
        
        avid=fs.put(decoded,
               filename=iq_user['name']+'.'+extension,
               contentType=mimetype)
        if iq_user.get('avatar',None):
            fs.delete(iq_user['avatar'][0])
        _ = yield objs.User.mupdate({'name':iq_user['name']},
                          {'$set':{'avatar':[avid,mimetype]}})
        defer.returnValue( True )
    pass

def version(iq,iq_user):
    #2010-12-10 21:55:29+0300 [XmlStream,client] 1292007329.38 - RECV: 
    #<iq from='blasux@blasux.ru/Gajim' to='bnw.blasux.ru' xml:lang='ru' type='get' id='496'>
    #   <query xmlns='jabber:iq:version'/>
    #</iq>
    
    if iq.query:
        if not 'jabber:iq:version' in iq.query.toXml(): # какого-то хуя не работает iq.query.getAttribute('xmlns','')
            return False
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id',None):
            reply['id'] = iq['id']
        reply.addElement('query')
        reply.query['xmlns'] = 'jabber:iq:version'
        reply.query.addElement('name',content='BnW')
        reply.query.addElement('version',content='0.1')
        reply.query.addElement('os',content='OS/360')
        send_raw(iq['from'],iq['to'],reply)
        return True
    pass

DISCO_ITEMS_XMLNS="http://jabber.org/protocol/disco#items"
def disco_items(iq,iq_user):
    if iq.query:
        if not DISCO_ITEMS_XMLNS in iq.query.toXml():
            return False
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id',None):
            reply['id'] = iq['id']
        reply.addElement('query')
        reply.query['xmlns'] = DISCO_ITEMS_XMLNS
        send_raw(iq['from'],iq['to'],reply)
        return True

DISCO_INFO_XMLNS="http://jabber.org/protocol/disco#info"
FEATURES = ('jabber:iq:version',
            'http://jabber.org/protocol/chatstates',
            'http://jabber.org/protocol/disco#info',
            'http://jabber.org/protocol/disco#items',
            'urn:xmpp:receipts',
)
def disco_info(iq,iq_user):
    if iq.query:
        if not DISCO_INFO_XMLNS in iq.query.toXml():
            return False
        reply = domish.Element((None,'iq'))
        reply['type'] = 'result'
        if iq.getAttribute('id',None):
            reply['id'] = iq['id']
        reply.addElement('query')
        reply.query['xmlns'] = DISCO_INFO_XMLNS
        reply.query.addElement('identity')
        reply.query.identity['category']='client' # not pretty sure
        reply.query.identity['type']='bot'
        reply.query.identity['name']='BnW'

        for feature_name in FEATURES:
            feature = reply.query.addElement('feature')
            feature['var'] = feature_name
    
        send_raw(iq['from'],iq['to'],reply)
        return True

handlers = [
    vcard_getav,
    version,
    disco_items,
    disco_info,
]
