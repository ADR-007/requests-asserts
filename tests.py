from http import HTTPStatus
from typing import Any, Dict, Tuple
from unittest import TestCase, TestResult

import requests
from requests import Response

from requests_asserts import RequestMock


class TestRequestsAsserts(TestCase):
    def test_no_request(self):
        def test(_self):
            with RequestMock.assert_requests([RequestMock(request_url='http://a.b.c')], _self):
                pass

        test_result, _ = self._run_test_case(test)

        self.assertEqual(1, len(test_result.failures))
        self.assertIn(
            'AssertionError: unexpectedly None : The pending request is missing!\n',
            test_result.failures[0][1]
        )

    def test_unexpected_request(self):
        def test(_self):
            with RequestMock.assert_requests([], _self):
                requests.get('http://a.b.c')

        test_result, _ = self._run_test_case(test)

        self.assertEqual(1, len(test_result.failures))
        self.assertIn(
            'AssertionError: unexpectedly None : This request is unexpected!\n',
            test_result.failures[0][1]
        )

    def test_all_parameters(self):
        default_mock_kwargs = dict(request_url='https://aa.bb.cc/', request_method=RequestMock.Method.POST)
        default_request_kwargs = dict(url='https://aa.bb.cc/', method='POST')

        for mock_parameter, mock_value, request_parameter, request_value, request_wrong_value, error_message in (
                (
                        'request_url', 'http://a.b',
                        'url', 'http://a.b', 'http://a.b.c', (
                                "AssertionError: 'http://a.b/' != 'http://a.b.c/'\n"
                                "- http://a.b/\n"
                                "+ http://a.b.c/\n"
                                "?           ++\n"
                                " : Wrong URL!\n"
                        )
                ),
                (
                        'request_method', RequestMock.Method.POST,
                        'method', 'POST', 'PUT', (
                                "AssertionError: 'POST' != 'PUT'\n"
                                "- POST\n"
                                "+ PUT\n"
                                " : Wrong method!\n"
                        )
                ),
                (
                        'request_json', {'a': 'b'},
                        'json', {'a': 'b'}, {'a': 'c'}, (
                                "AssertionError: {'a': 'b'} != {'a': 'c'}\n"
                                "- {'a': 'b'}\n?        ^\n"
                                "\n"
                                "+ {'a': 'c'}\n"
                                "?        ^\n"
                                " : Wrong body!\n"
                        )
                ),
                (
                        'request_json', {'a': 'b'},
                        'data', b'{"a": "b"}', b'{"a": ', (
                                "JSON is broken!\n"
                        )
                ),
                (
                        'request_body', b'123',
                        'data', b'123', b'124', (
                                "AssertionError: b'123' != b'124' : Wrong body\n"
                        )
                ),
                (
                        'request_headers', {
                            'User-Agent': 'python-requests/2.26.0',
                            'Accept-Encoding': 'gzip, deflate',
                            'Accept': '*/*',
                            'Connection': 'keep-alive',
                            'a': 'b',
                            'Content-Length': '0'
                        },
                        'headers', {'a': 'b'}, {'a': 'b', 'c': 'd'}, (
                                "AssertionError: {'Use[96 chars]tion': 'keep-alive', 'a': 'b', 'Content-Length': '0'} "
                                "!= {'Use[96 chars]tion': 'keep-alive', 'a': 'b', 'c': 'd', 'Content-Length': '0'} : "
                                "Wrong headers!\n"
                        )
                ),
                (
                        'request_headers_contains', {'a': 'b'},
                        'headers', {'a': 'b'}, {'a': 'e', 'c': 'd'}, (
                                "AssertionError: {'a': 'b'} != {'a': 'e'}\n"
                                "- {'a': 'b'}\n"
                                "?        ^\n"
                                "\n"
                                "+ {'a': 'e'}\n"
                                "?        ^\n"
                                " : Wrong headers!\n"
                        )
                ),

        ):
            with self.subTest(f'{mock_parameter} - correct'):
                self._assert_no_failures(
                    mock_kwargs={**default_mock_kwargs, mock_parameter: mock_value},
                    request_kwargs={**default_request_kwargs, request_parameter: request_value}
                )

            with self.subTest(f'{mock_parameter} - incorrect'):
                self._assert_failure(
                    mock_kwargs={**default_mock_kwargs, mock_parameter: mock_value},
                    request_kwargs={**default_request_kwargs, request_parameter: request_wrong_value},
                    error_message=error_message
                )

    def test_response(self):
        response = self._assert_no_failures(
            mock_kwargs=dict(
                request_url='http://a.b',
                response_json={'aa': 'bb'},
                response_status_code=HTTPStatus.ACCEPTED
            ),
            request_kwargs=dict(url='http://a.b', method='GET')
        )

        self.assertEqual(HTTPStatus.ACCEPTED.value, response.status_code)
        self.assertEqual({'aa': 'bb'}, response.json())

    def _run_test_case(self, func) -> Tuple[TestResult, Any]:
        result = []

        class FakeTest(TestCase):
            def test(self):
                result.append(func(self))

        return FakeTest('test').run(), result[0] if result else None

    def test_as_decorator(self):
        @RequestMock.assert_requests([RequestMock(request_url='http://a.b.c')])
        def test(_self):
            requests.get('http://a.b.c.d')

        test_result, _ = self._run_test_case(test)

        self.assertEqual(1, len(test_result.failures))
        self.assertIn(
            "AssertionError: 'http://a.b.c/' != 'http://a.b.c.d/'\n"
            "- http://a.b.c/\n"
            "+ http://a.b.c.d/\n"
            "?             ++\n"
            " : Wrong URL!\n",
            test_result.failures[0][1]
        )

    def test_several_requests(self):
        def test(_self):
            with RequestMock.assert_requests([
                RequestMock(request_url='http://a.b.c', response_json=1),
                RequestMock(request_url='http://a.b.c/1', response_json=2),
                RequestMock(request_url='http://a.b.c/2', response_json=3),
            ], _self):
                results_ = [requests.get('http://a.b.c').json()]

                try:
                    results_.append(requests.get('http://a.b.c/wrong'))
                except requests.exceptions.ConnectionError:
                    pass

                results_.append(requests.get('http://a.b.c/2'))

                return results_

        test_result, results = self._run_test_case(test)

        self.assertEqual(1, len(test_result.failures))
        self.assertIn(
            "AssertionError: 'http://a.b.c/1' != 'http://a.b.c/wrong'\n"
            "- http://a.b.c/1\n"
            "?              ^\n"
            "+ http://a.b.c/wrong\n"
            "?              ^^^^^\n"
            " : Wrong URL!\n",
            test_result.failures[0][1]
        )

    def _assert_no_failures(self, mock_kwargs: Dict[str, Any], request_kwargs: Dict[str, Any]) -> Response:
        def test(_self):
            with RequestMock.assert_requests([RequestMock(**mock_kwargs)], _self):
                return requests.request(**request_kwargs)

        test_result, response = self._run_test_case(test)

        self.assertFalse(test_result.failures)

        return response

    def _assert_failure(self, mock_kwargs: Dict[str, Any], request_kwargs: Dict[str, Any], error_message: str):
        def test(_self):
            with RequestMock.assert_requests([RequestMock(**mock_kwargs)], _self):
                return requests.request(**request_kwargs)

        test_result, _ = self._run_test_case(test)

        self.assertEqual(1, len(test_result.failures))
        self.assertIn(error_message, test_result.failures[0][1])
