import json
from enum import Enum
from functools import wraps
from http import HTTPStatus
from itertools import zip_longest
from typing import Any, Dict, List, NamedTuple, Optional
from unittest import TestCase

import requests
from requests import Request
from responses import mock as response_mock


__all__ = ['RequestMock', 'IGNORED']

IGNORED = object()


class AssertRequests:
    def __init__(self, request_mocks: List['RequestMock'], test_case: TestCase = None):
        self.request_mocks = request_mocks
        self.test_case = test_case

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            self.test_case = args[0]
            with self:
                return func(*args, **kwargs)

        return inner

    def __enter__(self):
        for request_mock in self.request_mocks:
            response_mock.add(
                method=request_mock.request_method.value,
                url=request_mock.request_url,
                json=request_mock.response_json,
                status=request_mock.response_status_code,
            )
        response_mock.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._check_requests(exc_val)

        finally:
            response_mock.__exit__(exc_type, exc_val, exc_tb)

        if exc_type is requests.exceptions.ConnectionError:
            return True

    def _check_requests(self, exc_val):
        for request_mock, mocked_call in zip_longest(self.request_mocks, response_mock.calls):
            request_mock: RequestMock

            request: Optional[Request] = mocked_call.request if mocked_call else None

            if request_mock:
                sub_test_name = f'{request_mock.request_method.value} {request_mock.request_url}'
            else:
                sub_test_name = f'[Unexpected] {request.method} {request.url}'

            with self.test_case.subTest(sub_test_name):
                try:
                    self.test_case.assertIsNotNone(request, 'The pending request is missing!')
                    self.test_case.assertIsNotNone(request_mock, 'This request is unexpected!')

                    self._assert_urls_equals(request_mock.request_url, request.url)
                    self.test_case.assertEqual(request_mock.request_method.value, request.method, 'Wrong method!')

                    if request_mock.request_json is not IGNORED:
                        self._assert_request_json_equal(request_mock.request_json, request.body)

                    if request_mock.request_body is not IGNORED:
                        self.test_case.assertEqual(request_mock.request_body, request.body, 'Wrong body')

                    if request_mock.request_headers is not IGNORED:
                        self.test_case.assertEqual(request_mock.request_headers, request.headers, 'Wrong headers!')

                    if request_mock.request_headers_contains is not IGNORED:
                        self.test_case.assertEqual(request_mock.request_headers_contains,
                                                   {key: value
                                                    for key, value in request.headers.items()
                                                    if key in request_mock.request_headers_contains},
                                                   'Wrong headers!')

                except AssertionError as error:
                    if exc_val:
                        raise error from exc_val

                    raise

    def _assert_urls_equals(self, expected_url: str, actual_url: str):
        if expected_url and actual_url and actual_url[-1] == '/' and expected_url[-1] != '/':
            expected_url += '/'

        self.test_case.assertEqual(expected_url, actual_url, 'Wrong URL!')

    def _assert_request_json_equal(self, expected_json, actual_body):
        try:
            self.test_case.assertEqual(
                expected_json,
                json.loads(actual_body),
                'Wrong body!'
            )

        except json.decoder.JSONDecodeError as error:
            raise AssertionError(f'JSON is broken!') from error


class RequestMock(NamedTuple):
    # noinspection PyUnresolvedReferences
    """
        Used to mock response and validate that the requests happened in the right order with right data

        Usage example:
            >>> import requests
            >>>
            >>> def get_likes_on_post(username, password, post_id):
            ...     access_token = requests.post('http://my.site/login',
            ...                                  json={'username': username, 'password': password}).json()['access_token']
            ...
            ...     likes = requests.get(f'http://my.site/posts/{post_id}',
            ...                          headers={'Accept': 'application/json',
            ...                                   'Authorization': f'Bearer {access_token}'}).json()['likes']
            ...
            ...     return likes
            >>>
            >>> class TestGetLikesOnPost(TestCase):
            ...     @RequestMock.assert_requests([
            ...         RequestMock(
            ...             request_url='http://my.site/login',
            ...             request_json={'username': 'the name', 'password': 'the password'},
            ...             request_method=RequestMock.Method.POST,
            ...             response_json={"access_token": 'the-token'}
            ...         ),
            ...         RequestMock(
            ...             request_url='http://my.site/posts/3',
            ...             request_headers_contains={'Authorization': 'Bearer the-token'},
            ...             response_json={'name': 'The cool story', 'likes': 42}
            ...         )
            ...     ])
            ...     def test_get_likes_on_post(self):
            ...         self.assertEqual(42, get_likes_on_post('the name', 'the password', 3))
            >>>
            >>> TestGetLikesOnPost('test_get_likes_on_post').run()
            <unittest.result.TestResult run=1 errors=0 failures=0>
        """

    class Method(Enum):
        POST = response_mock.POST
        GET = response_mock.GET
        PUT = response_mock.PUT
        PATCH = response_mock.PATCH
        DELETE = response_mock.DELETE
        HEAD = response_mock.HEAD
        OPTIONS = response_mock.OPTIONS

    request_url: str
    request_method: Method = Method.GET
    request_json: Any = IGNORED
    request_body: str = IGNORED
    request_headers: Dict[str, Any] = IGNORED
    request_headers_contains: Dict[str, Any] = IGNORED

    response_json: Any = None
    response_status_code: HTTPStatus = HTTPStatus.OK

    assert_requests = staticmethod(AssertRequests)  # can be used both as decorator or context manager
