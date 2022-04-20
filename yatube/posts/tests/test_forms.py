import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class FormTestsCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Ivan')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='first',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Vova')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(FormTestsCase.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post"""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовая запись',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        post = Post.objects.latest('id')
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(post.image, 'posts/small.gif')
        self.assertTrue(
            Post.objects.filter(
                group=self.group,
                text='Тестовая запись',
                image='posts/small.gif',
            ).exists()
        )
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertFormError(
            response,
            'form',
            'image',
            errors='Отправленный файл пуст.'
        )

    def test_create_post_edit(self):
        """Валидная форма изменяет запись в Post"""
        post_count = Post.objects.count()
        post = Post.objects.first()
        form_data = {
            'text': 'Редактирование тестовой записи',
            'group': self.group.id,
        }
        url = reverse('posts:post_edit', kwargs={'post_id': post.pk})
        response = self.author_client.post(
            url,
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.pk})
        )
        self.assertEqual(Post.objects.count(), post_count)
        post.refresh_from_db()
        self.assertEqual(post.text, form_data['text'])

    def test_add_comment(self):
        """Валидная форма создает комментарий"""
        post = FormTestsCase.post
        comment_count = 0

        url = reverse('posts:add_comment', kwargs={'post_id': post.pk})
        form_data = {
            'text': 'Тестовый комментарий',
        }

        self.guest_client.post(
            url,
            data=form_data,
            follow=True,
        )
        self.post.refresh_from_db()
        self.assertEqual(post.comments.count(), comment_count)

        clients = {
            self.authorized_client: comment_count,
            self.author_client: comment_count,
        }

        for client, count in clients.items():
            with self.subTest(client=client):
                count = post.comments.count()
                client.post(
                    url,
                    data=form_data,
                    follow=True,
                )
                self.post.refresh_from_db()
                self.assertEqual(post.comments.count(), count + 1)
                self.assertEqual(post.comments.last().text, form_data['text'])
