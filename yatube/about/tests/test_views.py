from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse


class StaticPagesViewsTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_about_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        temlpates_about_names = {
            'about/author.html': reverse('about:author'),
            'about/tech.html': reverse('about:tech'),
        }
        for template, reverse_name in temlpates_about_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_about_accessible_by_name(self):
        """URL, генерируемый при помощи Namespace About, доступен."""
        about_names = {
            reverse('about:author'): HTTPStatus.OK,
            reverse('about:tech'): HTTPStatus.OK,
        }
        for name, status in about_names.items():
            with self.subTest(name=name):
                response = self.guest_client.get(name)
                self.assertEqual(response.status_code, status)
