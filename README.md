Used to mock response and validate that the requests happened in the right order with right data

Usage example:
```py
import requests
from unittests import TestCase 

def get_likes_on_post(username, password, post_id):
    access_token = requests.post('http://my.site/login',
                                 json={'username': username, 'password': password}).json()['access_token']

    likes = requests.get(f'http://my.site/posts/{post_id}',
                         headers={'Accept': 'application/json',
                                  'Authorization': f'Bearer {access_token}'}).json()['likes']

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
