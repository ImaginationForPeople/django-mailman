# -*- coding: utf-8 -*-
import re
import urllib2
from types import UnicodeType

from django.db import models
from django.utils.translation import ugettext_lazy as _

from webcall import MultipartPostHandler

# Mailman-Messages for a successfull subscription
SUBSCRIBE_MSG = (
    u'Erfolgreich eingetragen', # de
    u'Successfully subscribed', # en
    u'Abonnement r\xe9ussi', # fr
)

# Mailman-Messages for successfully remove from a list
UNSUBSCRIBE_MSG = (
    u'Erfolgreich beendete Abonnements', # de
    u'Successfully Removed', # en
    u'Successfully Unsubscribed', # also en
    u'R\xe9siliation r\xe9ussie', # fr
)

# Mailman-Messages for a failed remove from a list
NON_MEMBER_MSG = (
    u'Nichtmitglieder können nicht aus der Mailingliste ausgetragen werden', # de
    u'Cannot unsubscribe non-members', # en
    u"Ne peut r\xe9silier l'abonnement de non-abonn\xe9s ", # fr
)

# To control user form unsubscription
UNSUBSCRIBE_BUTTON = {
    'fr' : 'Résilier',
}

# Definition from the Mailman-Source ../Mailman/Default.py
LANGUAGES = (
    ('utf-8',       _('Arabic')),
    ('utf-8',       _('Catalan')),
    ('iso-8859-2',  _('Czech')),
    ('iso-8859-1',  _('Danish')),
    ('iso-8859-1',  _('German')),
    ('us-ascii',    _('English (USA)')),
    ('iso-8859-1',  _('Spanish (Spain)')),
    ('iso-8859-15', _('Estonian')),
    ('iso-8859-15', _('Euskara')),
    ('iso-8859-1',  _('Finnish')),
    ('iso-8859-1',  _('French')),
    ('utf-8',       _('Galician')),
    ('utf-8',       _('Hebrew')),
    ('iso-8859-2',  _('Croatian')),
    ('iso-8859-2',  _('Hungarian')),
    ('iso-8859-15', _('Interlingua')),
    ('iso-8859-1',  _('Italian')),
    ('euc-jp',      _('Japanese')),
    ('euc-kr',      _('Korean')),
    ('iso-8859-13', _('Lithuanian')),
    ('iso-8859-1',  _('Dutch')),
    ('iso-8859-1',  _('Norwegian')),
    ('iso-8859-2',  _('Polish')),
    ('iso-8859-1',  _('Portuguese')),
    ('iso-8859-1',  _('Portuguese (Brazil)')),
    ('iso-8859-2',  _('Romanian')),
    ('koi8-r',      _('Russian')),
    ('utf-8',       _('Slovak')),
    ('iso-8859-2',  _('Slovenian')),
    ('utf-8',       _('Serbian')),
    ('iso-8859-1',  _('Swedish')),
    ('iso-8859-9',  _('Turkish')),
    ('utf-8',       _('Ukrainian')),
    ('utf-8',       _('Vietnamese')),
    ('utf-8',       _('Chinese (China)')),
    ('utf-8',       _('Chinese (Taiwan)')),
)

# POST-Data for a list subcription
SUBSCRIBE_DATA = {
    'subscribe_or_invite': '0',
    'send_welcome_msg_to_this_batch': '0',
    'notification_to_list_owner': '0',
    'adminpw': None,
    'subscribees_upload': None,
}

# POST-Data for a list removal
UNSUBSCRIBE_DATA = {
    'send_unsub_ack_to_this_batch': 0,
    'send_unsub_notifications_to_list_owner': 0,
    'adminpw': None,
    'unsubscribees_upload': None,
}

def check_encoding(value, encoding):
    if isinstance(value, UnicodeType) and encoding != 'utf-8':
        value = value.encode(encoding)
    if not isinstance(value, UnicodeType) and encoding == 'utf-8':
        value = unicode(value, errors='replace')
    return value


class List(models.Model):
    name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    main_url = models.URLField(verify_exists=False)
    encoding = models.CharField(max_length=20, choices=LANGUAGES)

    class Meta:
        verbose_name = 'List-Installation'
        verbose_name_plural = 'List-Installations'

    def __unicode__(self):
        return u'%s' % (self.name)

    def __parse_status_content(self, content):
        if not content:
            raise Exception('No valid Content!')

        m = re.search('(?<=<h5>).+(?=:[ ]{0,1}</h5>)', content)
        if m:
            msg = m.group(0).rstrip()
        else:
            m = re.search('(?<=<h3><strong><font color="#ff0000" size="\+2">)'+
                          '.+(?=:[ ]{0,1}</font></strong></h3>)', content)
            if m:
                msg = m.group(0)
            else:
                raise Exception('Could not find status message')

        m = re.search('(?<=<ul>\n<li>).+(?=\n</ul>\n)', content)
        if m:
            member = m.group(0)
        else:
            raise Exception('Could not find member-information')

        msg = msg.encode(self.encoding)
        member = member.encode(self.encoding)
        return (msg, member)

    def __parse_member_content(self, content, encoding='iso-8859-1'):
        if not content:
            raise Exception('No valid Content!')
        members = []
        letters = re.findall('letter=\w{1}', content)
        chunks = re.findall('chunk=\d+', content)
        input = re.findall('name=".+_realname" type="TEXT" value=".*" size="[0-9]+" >', content)
        for member in input:
            info = member.split('" ')
            email = re.search('(?<=name=").+(?=_realname)', info[0]).group(0)
            realname = re.search('(?<=value=").*', info[2]).group(0)
            email = unicode(email, encoding)
            realname = unicode(realname, encoding)
            members.append([realname, email])
        letters = set(letters)
        return (letters, members, chunks)

    def get_admin_moderation_url(self):
        return '%s/admindb/%s/?adminpw=%s' % (self.main_url, self.name,
                                              self.password)

    def subscribe(self, email, first_name=u'', last_name=u'', send_welcome_msg=False):
        from email.Utils import formataddr

        url = '%s/admin/%s/members/add' % (self.main_url, self.name)

        first_name = check_encoding(first_name, self.encoding)
        last_name = check_encoding(last_name, self.encoding)
        email = check_encoding(email, self.encoding)
        name = '%s %s' % (first_name, last_name)

        SUBSCRIBE_DATA['adminpw'] = self.password
        SUBSCRIBE_DATA['send_welcome_msg_to_this_batch'] = send_welcome_msg
        SUBSCRIBE_DATA['subscribees_upload'] = formataddr([name.strip(), email])
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding, True))
        content = opener.open(url, SUBSCRIBE_DATA).read()

        (msg, member) = self.__parse_status_content(unicode(content, self.encoding))
        if (msg not in SUBSCRIBE_MSG):
            error = u'%s: %s' % (unicode(msg, encoding=self.encoding), unicode(member, encoding=self.encoding))
            raise Exception(error.encode(self.encoding))

    def unsubscribe(self, email):
        url = '%s/admin/%s/members/remove' % (self.main_url, self.name)

        email = check_encoding(email, self.encoding)
        UNSUBSCRIBE_DATA['adminpw'] = self.password
        UNSUBSCRIBE_DATA['unsubscribees_upload'] = email
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding))
        content = opener.open(url, UNSUBSCRIBE_DATA).read()

        (msg, member) = self.__parse_status_content(content)
        if (msg not in UNSUBSCRIBE_MSG) and (msg not in NON_MEMBER_MSG):
            error = u'%s: %s' % (msg, member)
            raise Exception(error.encode(self.encoding))

    def get_all_members(self):
        url = '%s/admin/%s/members/list' % (self.main_url, self.name)
        data = { 'adminpw': self.password }
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding))

        all_members = []
        content = opener.open(url, data).read()
        (letters, members, chunks) = self.__parse_member_content(content, self.encoding)
        all_members.extend(members)
        for letter in letters:
            url_letter = u"%s?%s" %(url, letter)
            content = opener.open(url_letter, data).read()
            (letters, members, chunks) = self.__parse_member_content(content, self.encoding)
            all_members.extend(members)
            for chunk in chunks[1:]:
                url_letter_chunk = "%s?%s&%s" %(url, letter, chunk)
                content = opener.open(url_letter_chunk, data).read()
                (letters, members, chunks) = self.__parse_member_content(content, self.encoding)
                all_members.extend(members)

        members = {}
        for m in all_members:
            email = m[1].replace(u"%40", u"@")
            members[email] = m[0]
        all_members = [(email, name) for email, name in members.items()]
        all_members.sort()
        return all_members

    def user_subscribe(self, email, password, language='fr', first_name=u'', last_name=u''):

        url = '%s/subscribe/%s' % (self.main_url, self.name)

        password = check_encoding(password, self.encoding)
        email = check_encoding(email, self.encoding)
        first_name = check_encoding(first_name, self.encoding)
        last_name = check_encoding(last_name, self.encoding)
        name = '%s %s' % (first_name, last_name)

        SUBSCRIBE_DATA['email'] = email
        SUBSCRIBE_DATA['pw'] = password
        SUBSCRIBE_DATA['pw-conf'] = password
        SUBSCRIBE_DATA['fullname'] = name
        SUBSCRIBE_DATA['language'] = language
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding, True))
        request = opener.open(url, SUBSCRIBE_DATA)
        content = request.read()
        for status in SUBSCRIBE_MSG:
            if len(re.findall(status, content)) > 0:
                return True
        raise Exception(content)

    def user_subscribe(self, email, password, language='fr', first_name=u'', last_name=u''):

        url = '%s/subscribe/%s' % (self.main_url, self.name)

        password = check_encoding(password, self.encoding)
        email = check_encoding(email, self.encoding)
        first_name = check_encoding(first_name, self.encoding)
        last_name = check_encoding(last_name, self.encoding)
        name = '%s %s' % (first_name, last_name)

        SUBSCRIBE_DATA['email'] = email
        SUBSCRIBE_DATA['pw'] = password
        SUBSCRIBE_DATA['pw-conf'] = password
        SUBSCRIBE_DATA['fullname'] = name
        SUBSCRIBE_DATA['language'] = language
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding, True))
        request = opener.open(url, SUBSCRIBE_DATA)
        content = request.read()
        # no error code to process

    def user_unsubscribe(self, email, language='fr'):

        url = '%s/options/%s/%s' % (self.main_url, self.name, email)

        email = check_encoding(email, self.encoding)

        UNSUBSCRIBE_DATA['email'] = email
        UNSUBSCRIBE_DATA['language'] = language
        UNSUBSCRIBE_DATA['login-unsub'] = UNSUBSCRIBE_BUTTON[language]
        
        opener = urllib2.build_opener(MultipartPostHandler(self.encoding, True))
        request = opener.open(url, UNSUBSCRIBE_DATA)
        content = request.read()
        # no error code to process
