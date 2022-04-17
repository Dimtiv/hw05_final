import shutil
import tempfile
import time
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post
from posts.views import LIMIT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivan')
        cls.test_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='test.gif',
            content=cls.test_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост тестирования URL',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Petr')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон Views-функций."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

        url_post_edit = reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post.pk}
        )
        templates_page_names[url_post_edit] = 'posts/create_post.html'
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_context_index(self):
        """В шаблон Views-функци index передан правильный контекст."""
        response = self.guest_client.get(reverse('posts:index'))
        page_obj = response.context['page_obj'][0]
        page_context = {
            page_obj.author.username: 'Ivan',
            page_obj.text: 'Тестовый пост тестирования URL',
            page_obj.group.title: 'Тестовая группа',
            page_obj.image: PostPagesTests.post.image,
        }
        for page_field, test_text in page_context.items():
            with self.subTest(page_field=page_field):
                self.assertEqual(page_field, test_text)

    def test_context_post_detil(self):
        """В шаблон Views-функци post_detil передан правильный контекст."""
        url = reverse(
            'posts:post_detail',
            kwargs={'post_id': PostPagesTests.post.pk}
        )
        response = self.authorized_client.get(url)
        page_obj = response.context.get('post')
        page_context = {
            page_obj.author.username: 'Ivan',
            page_obj.text: 'Тестовый пост тестирования URL',
            page_obj.image: PostPagesTests.post.image,
        }
        for page_field, test_text in page_context.items():
            with self.subTest(page_field=page_field):
                self.assertEqual(page_field, test_text)

    def test__context_group_list(self):
        """В шаблон Views-функци group_posts передан правильный контекст."""
        url = reverse(
            'posts:group_list',
            kwargs={'slug': PostPagesTests.group.slug}
        )
        response = self.guest_client.get(url)
        page_obj = response.context['page_obj'][0]
        page_context = {
            page_obj.author.username: 'Ivan',
            page_obj.text: 'Тестовый пост тестирования URL',
            page_obj.group.title: 'Тестовая группа',
            page_obj.group.slug: 'test-slug',
            page_obj.group.description: 'Тестовое описание',
            page_obj.image: PostPagesTests.post.image,
        }
        for page_field, test_text in page_context.items():
            with self.subTest(page_field=page_field):
                self.assertEqual(page_field, test_text)

    def test__context_profile(self):
        """В шаблон Views-функци profile передан правильный контекст."""
        url = reverse(
            'posts:profile',
            kwargs={'username': PostPagesTests.user.username}
        )
        response = self.authorized_client.get(url)
        page_obj = response.context['page_obj'][0]
        page_context = {
            page_obj.author.username: 'Ivan',
            page_obj.text: 'Тестовый пост тестирования URL',
            len(response.context.get('page_obj')): 1,
            page_obj.image: PostPagesTests.post.image,
        }
        for page_field, test_text in page_context.items():
            with self.subTest(page_field=page_field):
                self.assertEqual(page_field, test_text)

    def test__get_context_great_create(self):
        """В шаблон Views-функци post_create передан правильный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test__post_great_create(self):
        """" Создание нового поста, метод POST"""
        data_form = {
            'text': 'Новый текст',
            'group': self.group.id,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=data_form,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.post.refresh_from_db()
        self.assertEqual(Post.objects.latest('id').text, data_form['text'])

    def test__get_context_great_edit(self):
        """В шаблон Views-функци post_edit передан правильный контекст."""
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        response = self.author_client.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        form = response.context.get('form')
        self.assertEqual(form.instance, self.post)
        self.assertEqual(response.context.get('post_id'), self.post.pk)
        self.assertTrue(response.context.get('is_edit'))
        response = self.authorized_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_comment_on_page(self):
        """Комментарий отобразился на странице"""
        post = PostPagesTests.post
        count_post = post.comments.count()
        url = reverse('posts:add_comment', kwargs={'post_id': post.pk})
        data_form = {
            'text': 'Тестовый комментарий',
        }

        response = self.authorized_client.post(
            url,
            data=data_form,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.post.refresh_from_db()
        self.assertEqual(post.comments.latest('id').text, data_form['text'])
        self.assertEqual(post.comments.count(), count_post + 1)


class PaginatorViewsTest(TestCase):
    """Паджинатор отражает верное количество постов на странице"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Boris')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.count_posts = 15
        for num in range(cls.count_posts):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост №{num}',
                group=cls.group
            )
            time.sleep(0.1)

    def setUp(self):
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        page_names = {
            reverse('posts:index'): LIMIT,
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                LIMIT,
            reverse('posts:profile', kwargs={'username': self.user}): LIMIT,
        }
        for page_name, limit in page_names.items():
            with self.subTest(page_name=page_name):
                response = self.guest_client.get(page_name)
                self.assertEqual(len(response.context['page_obj']), limit)

        for page_name, limit in page_names.items():
            with self.subTest(page_name=page_name):
                response = self.guest_client.get(page_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    PaginatorViewsTest.count_posts - limit
                )


class PastAdPageTest(TestCase):
    """Проверка при создании поста. Пост отображается на страницах"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Boris')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='test-slug1',
            description='Тестовое описание1',
        )
        cls.group_test = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text=f'Тестовый пост группы {cls.group.title}',
            group=cls.group
        )

    def setUp(self):
        self.user = User.objects.create_user(username='Petr')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_add_to_page(self):
        """Пост отразился на главной странице, в профайле и в группе"""
        dict_url = {
            reverse('posts:index'): 0,
            reverse(
                'posts:group_list',
                kwargs={'slug': PastAdPageTest.group.slug}): 0,
            reverse(
                'posts:profile',
                kwargs={'username': PastAdPageTest.user.username}): 0,
        }
        for url in dict_url:
            response = self.authorized_client.get(url)
            dict_url[url] = len(response.context['page_obj'])

        Post.objects.create(
            author=PastAdPageTest.user,
            text='Тестовый пост группы тестирования довабления записи',
            group=PastAdPageTest.group
        )

        for url, count in dict_url.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(
                    len(response.context['page_obj']),
                    count + 1
                )

        url_slug = reverse(
            'posts:group_list',
            kwargs={'slug': PastAdPageTest.group.slug}
        )
        response = self.authorized_client.get(url_slug)
        self.assertNotEqual(
            response.context['group'].slug,
            PastAdPageTest.group_test.slug
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FollowTest(TestCase):
    """Тестирование подписки на избранных авторов"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Boris')
        cls.group = Group.objects.create(
            title='Тестовая группа1',
            slug='test-slug1',
            description='Тестовое описание1',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=f'Тестовый пост группы {cls.group.title}',
            group=cls.group
        )
        cls.url = reverse('posts:follow_index')

    def setUp(self):
        self.user_follower = User.objects.create_user(username='Petr')
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.user_follower)
        self.user_no_follower = User.objects.create_user(username='Ivan')
        self.authorized_no_follower = Client()
        self.authorized_no_follower.force_login(self.user_no_follower)
        self.author_client = Client()
        self.author_client.force_login(FollowTest.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_follow_on_author(self):
        """
        Авторизированный пользователь добавляет/удаляет подписки на автора
        """
        post_author_count = Post.objects.count()
        Follow.objects.get_or_create(
            user=self.user_follower,
            author=FollowTest.user)
        dict_client = {
            self.authorized_follower: post_author_count,
            self.authorized_no_follower: 0,
        }
        for client, count in dict_client.items():
            with self.subTest(client=client):
                response = client.get(FollowTest.url)
                self.assertEqual(
                    len(response.context['page_obj']),
                    count
                )
        Follow.objects.filter(
            user=self.user_follower,
            author=FollowTest.user).delete()
        response = self.authorized_follower.get(FollowTest.url)
        post_folower_count = len(response.context['page_obj'])
        self.assertNotEqual(post_author_count, post_folower_count)

    def test_follow_add_post(self):
        """Отражение нового поста в ленте подписчика"""
        Follow.objects.get_or_create(
            user=self.user_follower,
            author=FollowTest.user
        )
        response = self.authorized_follower.get(FollowTest.url)
        post_folower_count_before = len(response.context['page_obj'])
        response = self.authorized_no_follower.get(FollowTest.url)
        post_no_folower_count_before = len(response.context['page_obj'])
        Post.objects.create(
            author=FollowTest.user,
            text='Тестовый пост тестирования подписок'
        )
        response = self.authorized_follower.get(FollowTest.url)
        post_folower_count_after = len(response.context['page_obj'])
        response = self.authorized_no_follower.get(FollowTest.url)
        post_no_folower_count_after = len(response.context['page_obj'])
        self.assertNotEqual(
            post_folower_count_before,
            post_folower_count_after,
        )
        self.assertEqual(
            post_no_folower_count_before,
            post_no_folower_count_after,
        )
