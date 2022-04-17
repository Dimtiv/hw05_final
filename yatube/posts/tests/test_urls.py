from http import HTTPStatus
from pickle import TRUE

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    """Проверка доступности URL адресов"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivan')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост тестирования URL',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Petr')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostURLTests.user)

    def test_url_guest_client(self):
        """Проверка доступности URL адресов неавторизованным пользователем"""
        list_url = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Ivan/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/no_page/': HTTPStatus.NOT_FOUND,
        }
        for address, status in list_url.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_url_guest_client(self):
        """Проверка редиректа неавторизованным пользователем """
        list_url = {
            '/posts/1/edit/': '/auth/login/?next=/posts/1/edit/',
            '/create/': '/auth/login/?next=/create/',
            '/posts/1/comment/': '/auth/login/?next=/posts/1/comment/',
        }
        for address, redirect_address in list_url.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=TRUE)
                self.assertRedirects(response, redirect_address)

    def test_url_authorized_client(self):
        """Проверка доступности URL адресов авторизованным пользователем"""
        list_url = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Ivan/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/no_page/': HTTPStatus.NOT_FOUND,
            '/posts/1/comment/': HTTPStatus.FOUND,
        }
        for address, status in list_url.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_url_author_client(self):
        """Проверка доступности URL адресов авторизированным автором"""
        list_url = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Ivan/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/no_page/': HTTPStatus.NOT_FOUND,
            '/posts/1/comment/': HTTPStatus.FOUND,
        }
        for address, status in list_url.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertEqual(response.status_code, status)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Ivan/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

        response = self.author_client.get('/posts/1/edit/')
        self.assertTemplateUsed(
            response,
            'posts/create_post.html', 'Шаблона редактирования поста автором'
        )

    def test_cache_index(self):
        """Тестирование кеширования главной страницы"""
        response = self.authorized_client.get(reverse('posts:index'))
        post_cache = response.content
        self.post.delete()
        response_new = self.authorized_client.get(reverse('posts:index'))
        post_new = response_new.content
        self.assertEqual(post_cache, post_new)
        cache.clear()
        response_test = self.authorized_client.get(reverse('posts:index'))
        post_text = response_test.context
        self.assertNotEqual(post_cache, post_text)
