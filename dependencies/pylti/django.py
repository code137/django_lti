# -*- coding: utf-8 -*-
"""
    PyLTI decorator implementation for django
"""
from __future__ import absolute_import
from django.http import HttpResponse

from .lti_settings import *

from functools import wraps
import json
import os

# Get an instance of a logger
import logging

log = logging.getLogger('django')

from inspect import getmembers
from pprint import pprint

from .common import (
    LTI_SESSION_KEY,
    LTI_PROPERTY_LIST,
    LTI_ROLES,
    verify_request_common,
    post_message,
    post_message2,
    generate_request_xml,
    LTIException,
    LTIRoleException,
    LTINotInSessionException,
    LTIPostMessageException
)


def default_error(request, error="n/a"):
    return HttpResponse("Error: " + error)


class LTI(object):
    def __init__(self, request, lti_args, lti_kwargs):
        self.request = request
        self.session = request.session
        self.lti_args = lti_args
        self.lti_kwargs = lti_kwargs
        self.nickname = self.name

        for thing in lti_kwargs:
            print(thing)

    @property
    def name(self):  # pylint: disable=no-self-use
        """
        Name returns user's name or user's email or user_id
        :return: best guess of name to use to greet user
        """
        if 'lis_person_sourcedid' in self.session:
            return self.session['lis_person_sourcedid']
        elif 'lis_person_contact_email_primary' in self.session:
            return self.session['lis_person_contact_email_primary']
        elif 'user_id' in self.session:
            return self.session['user_id']
        else:
            return ''

    @property
    def user_id(self):  # pylint: disable=no-self-use
        """
        Returns user_id as provided by LTI

        :return: user_id
        """
        return self.session['user_id']

    def verify(self):
        """
        Verify if LTI request is valid, validation
        depends on @lti wrapper arguments

        :raises: LTIException
        """
        log.debug('verify request=%s', self.lti_kwargs.get('req_type'))
        if self.lti_kwargs.get('req_type') == 'session':
            self._verify_session()
        elif self.lti_kwargs.get('req_type') == 'initial':
            self.verify_request()
        else:
            raise LTIException("Unknown request type")
        return True

    def _verify_session(self):
        """
        Verify that session was already created

        :raises: LTIException
        """
        if not self.session.get(LTI_SESSION_KEY, False):
            log.debug('verify_session failed')
            raise LTINotInSessionException('Session expired or unavailable')

    def _verify_any(self):
        """
        Verify that request is in session or initial request

        :raises: LTIException
        """
        log.debug('verify_any enter')
        try:
            self._verify_session()
        except LTINotInSessionException:
            self.verify_request()

    def _consumers(self):
        return CONSUMERS

    def verify_request(self):
        """
        Verify LTI request
        :raises: LTIException if request validation failed
        """

        # the full request path url with parameters
        url = self.request.build_absolute_uri(self.request.get_full_path())
        headers = self.request.META

        consumers = self._consumers()

        # we copy the params to make them mutable
        if self.request.method == 'POST':
            params = self.request.POST.copy()
        else:
            params = self.request.GET.copy()
        try:
            verify_request_common(consumers, url,
                                  self.request.method, headers,
                                  params)
            log.debug('verify_request success')

            # All good to go, store all of the LTI params into a
            # self.session dict for use in views
            for prop in LTI_PROPERTY_LIST:
                if params.get(prop, None):
                    self.session[prop] = params[prop]

            # Set logged in self.session key
            self.session[LTI_SESSION_KEY] = True
            return True
        except LTIException:
            log.debug('verify_request failed')
            for prop in LTI_PROPERTY_LIST:
                if self.session.get(prop, None):
                    del self.session[prop]

            self.session[LTI_SESSION_KEY] = False
            raise

    def _check_role(self):
        """
        Check that user is in role specified as wrapper attribute

        :exception: LTIException if user is not in roles
        """
        log.debug("Checking for roles")
        log.debug(self.lti_kwargs)
        role = u'any'
        if 'role' in self.lti_kwargs:
            role = self.lti_kwargs['role']
        log.debug(
                "check_role lti_role=%s decorator_role=%s", self.role, role
        )
        if not (role == u'any' or self.is_role(role)):
            raise LTIRoleException('Not authorized.')

    def role(self):  # pylint: disable=no-self-use
        """
        LTI roles

        :return: roles
        """
        return self.session.get('roles')

    def is_role(self, role):
        """
        Verify if user is in role

        :param: role: role to verify against
        :return: if user is in role
        :exception: LTIException if role is unknown
        """
        log.debug("is_role %s", role)
        roles = self.session['roles'].split(',')
        if role in LTI_ROLES:
            role_list = LTI_ROLES[role]
            # find the intersection of the roles
            roles = set(role_list) & set(roles)
            is_user_role_there = len(roles) >= 1
            log.debug(
                    "is_role roles_list=%s role=%s in list=%s", role_list,
                    roles, is_user_role_there
            )
            return is_user_role_there
        else:
            raise LTIException("Unknown role {}.".format(role))

    @property
    def key(self):  # pylint: disable=no-self-use
        """
        OAuth Consumer Key
        :return: key
        """
        return str(self.session['oauth_consumer_key'])

    @property
    def response_url(self):
        """
        Returns remapped lis_outcome_service_url
        uses PYLTI_URL_FIX map to support edX dev-stack

        :return: remapped lis_outcome_service_url
        """
        url = self.session['lis_outcome_service_url']
        urls = PYLTI_URL_FIX = {
            "https://localhost:8000/": {
                "https://localhost:8000/": "http://localhost:8000/"
            },
            "https://localhost/": {
                "https://localhost/": "http://192.168.33.10/"
            }
        }

        # url remapping is useful for using devstack
        # devstack reports httpS://localhost:8000/ and listens on HTTP
        for prefix, mapping in urls.items():
            if url.startswith(prefix):
                for _from, _to in mapping.items():
                    url = url.replace(_from, _to)
        return url

    @staticmethod
    def message_identifier_id():
        """
        Message identifier to use for XML callback

        :return: non-empty string
        """
        return "edX_fix"

    @property
    def lis_result_sourcedid(self):  # pylint: disable=no-self-use
        """
        lis_result_sourcedid to use for XML callback

        :return: LTI lis_result_sourcedid
        """
        return self.session['lis_result_sourcedid']

    def post_grade(self, grade):
        """
        Post grade to LTI consumer using XML

        :param: grade: 0 <= grade <= 1
        :return: True is post successful and grade valid
        :exception: LTIPostMessageException if call failed
        """
        message_identifier_id = self.message_identifier_id()
        operation = 'replaceResult'
        lis_result_sourcedid = self.lis_result_sourcedid
        # # edX devbox fix
        score = float(grade)
        if 0 <= score <= 1.0:
            xml = generate_request_xml(
                    message_identifier_id, operation, lis_result_sourcedid,
                    score)
            ret = post_message(self._consumers(), self.key,
                               self.response_url, xml)
            if not ret:
                raise LTIPostMessageException("Post Message Failed")
            return True

        return False

    def post_grade2(self, grade, user=None, comment=''):
        """
        Post grade to LTI consumer using REST/JSON
        URL munging will is related to:
        https://openedx.atlassian.net/browse/PLAT-281

        :param: grade: 0 <= grade <= 1
        :return: True is post successful and grade valid
        :exception: LTIPostMessageException if call failed
        """
        content_type = 'application/vnd.ims.lis.v2.result+json'
        if user is None:
            user = self.user_id
        lti2_url = self.response_url.replace(
                "/grade_handler",
                "/lti_2_0_result_rest_handler/user/{}".format(user))
        score = float(grade)
        if 0 <= score <= 1.0:
            body = json.dumps({
                "@context": "http://purl.imsglobal.org/ctx/lis/v2/Result",
                "@type": "Result",
                "resultScore": score,
                "comment": comment
            })
            ret = post_message2(self._consumers(), self.key, lti2_url, body,
                                method='PUT',
                                content_type=content_type)
            if not ret:
                raise LTIPostMessageException("Post Message Failed")
            return True

        return False


# lti simple wrapper wrapper
def lti(*lti_args, **lti_kwargs):
    def _lti(function):

        @wraps(function)
        def wrapper(request, *args, **kwargs):
            """
            Pass LTI reference to function or return error.
            """
            try:
                the_lti = LTI(request, lti_args, lti_kwargs)
                the_lti.verify()
                the_lti._check_role()
                kwargs['lti'] = the_lti
                return function(request, *args, **kwargs)
            except LTIException as lti_exception:
                # throw exceptions up to a default_error view
                return default_error(request, error=str(lti_exception))

        return wrapper

    return _lti
