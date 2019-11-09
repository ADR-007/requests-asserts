# Requests-Asserts

[![CircleCI](https://circleci.com/gh/ADR-007/requests-asserts.svg?style=svg)](https://circleci.com/gh/ADR-007/requests-asserts)
[![Coverage Status](https://coveralls.io/repos/github/ADR-007/requests-asserts/badge.svg?branch=master)](https://coveralls.io/github/ADR-007/requests-asserts?branch=master)
[![PyPI version](https://badge.fury.io/py/requests-asserts.svg)](https://badge.fury.io/py/requests-asserts)
![PyPI - License](https://img.shields.io/pypi/l/requests-asserts)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/requests-asserts)
![PyPI - Status](https://img.shields.io/pypi/status/requests-asserts)

The decorator and context manager to mock and verify HTTP requests made by `requests` library for `unittest`.

## How to install

```
pip install requests-asserts
```

## How to use

Make a list of `RequestMock` elements that contain all information about the expected request and response.
Use `RequestMock.assert_requests(request_mocks)` with the list as a decorator or context manager.

### Example
```py
import requests
from unittests import TestCase 

def get_likes_on_post(username, password, post_id):
    access_token = requests.post(
        'http://my.site/login',
        json={'username': username, 'password': password}
    ).json()['access_token']

    likes = requests.get(
        f'http://my.site/posts/{post_id}',
        headers={
            'Accept': 'application/json', 
            'Authorization': f'Bearer {access_token}'
        }
    ).json()['likes']

    return likes

class TestGetLikesOnPost(TestCase):
    @RequestMock.assert_requests([
        RequestMock(
            request_url='http://my.site/login',
            request_json={'username': 'the name', 'password': 'the password'},
            request_method=RequestMock.Method.POST,
            response_json={"access_token": 'the-token'}
        ),
        RequestMock(
            request_url='http://my.site/posts/3',
            request_headers_contains={'Authorization': 'Bearer the-token'},
            response_json={'name': 'The cool story', 'likes': 42}
        )
    ])
    def test_get_likes_on_post(self):
        self.assertEqual(42, get_likes_on_post('the name', 'the password', 3))

```
