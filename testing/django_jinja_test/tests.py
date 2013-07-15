# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from django.http import HttpResponse
from django.test import signals, TestCase
from django.test.client import RequestFactory
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse

from django_jinja.base import env, dict_from_context, Template

import datetime
import sys

class TemplateFunctionsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def tearDown(self):
        pass

    def test_template_filters(self):
        filters_data = [
            ("{{ 'test-1'|reverseurl }}", {}, '/test1/'),
            ("{{ 'test-1'|reverseurl(data=2) }}", {}, '/test1/2/'),
            ("{{ num|floatformat }}", {'num': 34.23234}, '34.2'),
            ("{{ num|floatformat(3) }}", {'num': 34.23234}, '34.232'),
            ("{{ 'hola'|capfirst }}", {}, "Hola"),
            ("{{ 'hola mundo'|truncatechars(5) }}", {}, "ho..."),
            ("{{ 'hola mundo'|truncatewords(1) }}", {}, "hola ..."),
            ("{{ 'hola mundo'|truncatewords_html(1) }}", {}, "hola ..."),
            ("{{ 'hola mundo'|wordwrap(1) }}", {}, "hola\nmundo"),
            ("{{ 'hola mundo'|title }}", {}, "Hola Mundo"),
            ("{{ 'hola mundo'|slugify }}", {}, "hola-mundo"),
            ("{{ 'hello'|ljust(10) }}", {}, "hello     "),
            ("{{ 'hello'|rjust(10) }}", {}, "     hello"),
            ("{{ 'hello\nworld'|linebreaksbr }}", {}, "hello<br />world"),
            ("{{ '<div>hello</div>'|removetags('div') }}", {}, "hello"),
            ("{{ '<div>hello</div>'|striptags }}", {}, "hello"),
            ("{{ list|join(',') }}", {'list':['a','b']}, 'a,b'),
            ("{{ 3|add(2) }}", {}, "5"),
            ("{{ now|date('n Y') }}", {"now": datetime.datetime(2012, 12, 20)}, "12 2012"),
        ]

        print()
        for template_str, kwargs, result in filters_data:
            print("- Testing: ", template_str, "with:", kwargs)
            template = env.from_string(template_str)
            _result = template.render(kwargs)
            self.assertEqual(_result, result)

    def test_custom_addons_01(self):
        template = env.from_string("{{ 'Hello'|replace('H','M') }}")
        result = template.render({})

        self.assertEqual(result, "Mello")

    def test_custom_addons_02(self):
        template = env.from_string("{% if m is one %}Foo{% endif %}")
        result = template.render({'m': 1})

        self.assertEqual(result, "Foo")

    def test_custom_addons_03(self):
        template = env.from_string("{{ myecho('foo') }}")
        result = template.render({})

        self.assertEqual(result, "foo")

    def test_autoescape_01(self):
        old_autoescape_value = env.autoescape
        env.autoescape = True

        template = env.from_string("{{ foo|safe }}")
        result = template.render({'foo': '<h1>Hellp</h1>'})
        self.assertEqual(result, "<h1>Hellp</h1>")

        env.autoescape = old_autoescape_value

    def test_autoescape_02(self):
        old_autoescape_value = env.autoescape
        env.autoescape = True

        template = env.from_string("{{ foo }}")
        result = template.render({'foo': '<h1>Hellp</h1>'})
        self.assertEqual(result, "&lt;h1&gt;Hellp&lt;/h1&gt;")

        env.autoescape = old_autoescape_value

    def test_csrf_01(self):
        template_content = "{% csrf_token %}"

        request = self.factory.get('/customer/details')
        if sys.version_info[0] < 3:
            request.META["CSRF_COOKIE"] = b'1234123123'
        else:
            request.META["CSRF_COOKIE"] = '1234123123'

        context = dict_from_context(RequestContext(request))

        template = env.from_string(template_content)
        result = template.render(context)
        self.assertEqual(result, "<input type='hidden' name='csrfmiddlewaretoken' value='1234123123' />")

    def test_cache_01(self):
        template_content = "{% cache 200 'fooo' %}foo bar{% endcache %}"

        request = self.factory.get('/customer/details')
        context = dict_from_context(RequestContext(request))

        template = env.from_string(template_content)
        result = template.render(context)

        self.assertEqual(result, "foo bar")

    def test_404_page(self):
        response = self.client.get(reverse("page-404"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, "404")

    def test_403_page(self):
        response = self.client.get(reverse("page-403"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, "403")

    def test_500_page(self):
        response = self.client.get(reverse("page-500"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, "500")


class TemplateDebugSignalsTest(TestCase):

    def setUp(self):
        signals.template_rendered.connect(self._listener)

    def tearDown(self):
        signals.template_rendered.disconnect(self._listener)
        signals.template_rendered.disconnect(self._fail_listener)

    def _listener(self, sender=None, template=None, **kwargs):
        self.assertTrue(isinstance(sender, Template))
        self.assertTrue(isinstance(template, Template))

    def _fail_listener(self, *args, **kwargs):
        self.fail("I shouldn't be called")

    def test_render(self):
        with self.settings(TEMPLATE_DEBUG=True):
            tmpl = Template("OK")
            tmpl.render()

    def test_render_without_template_debug_setting(self):
        signals.template_rendered.connect(self._fail_listener)

        with self.settings(TEMPLATE_DEBUG=False):
            tmpl = Template("OK")
            tmpl.render()

    def test_stream(self):
        with self.settings(TEMPLATE_DEBUG=True):
            tmpl = Template("OK")
            tmpl.stream()

    def test_stream_without_template_debug_setting(self):
        signals.template_rendered.connect(self._fail_listener)

        with self.settings(TEMPLATE_DEBUG=False):
            tmpl = Template("OK")
            tmpl.stream()

    def test_template_used(self):
        """
        Test TestCase.assertTemplateUsed with django-jinja template
        """
        template_name = 'test.jinja'

        def view(request, template_name):
            tmpl = Template("{{ test }}")
            return HttpResponse(tmpl.stream({"test": "success"}))

        with self.settings(TEMPLATE_DEBUG=True):
            request = RequestFactory().get('/')
            response = view(request, template_name=template_name)
            self.assertTemplateUsed(response, template_name)
            self.assertEqual(response.content, "success")
