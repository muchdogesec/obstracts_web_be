from django.test import SimpleTestCase, TestCase

from ...users.models import CustomUser
from ..slug import get_next_slug, get_next_unique_slug, get_next_unique_slug_value


class NextSlugTest(SimpleTestCase):
    def test_next_slug_basic(self):
        self.assertEqual("slug-11", get_next_slug("slug", 11))

    def test_next_slug_truncate(self):
        self.assertEqual("slug-11", get_next_slug("slug", 11, max_length=7))
        self.assertEqual("slu-11", get_next_slug("slug", 11, max_length=6))
        self.assertEqual("slu-100", get_next_slug("slug", 100, max_length=7))
        self.assertEqual("sl-100", get_next_slug("slug", 100, max_length=6))

    def test_next_slug_fail(self):
        with self.assertRaises(ValueError):
            get_next_slug("slug", 11111, max_length=6)


class NextUniqueSlugTest(TestCase):
    # we test with CustomUsers because that's a model we know exists in the project.
    def test_basic(self):
        self.assertEqual("slug", get_next_unique_slug(CustomUser, "Slug", "username"))
        self.assertEqual(
            "slug", get_next_unique_slug_value(CustomUser, "slug", "username")
        )
        user = CustomUser(username="slug")
        user.save()
        self.assertEqual("slug-2", get_next_unique_slug(CustomUser, "Slug", "username"))
        self.assertEqual(
            "slug-2", get_next_unique_slug_value(CustomUser, "slug", "username")
        )

    def test_extra_filter_args(self):
        CustomUser.objects.create(username="u1", first_name="alice", last_name="slug")
        self.assertEqual(
            "slug-2",
            get_next_unique_slug_value(
                CustomUser,
                "slug",
                "last_name",
                extra_filter_args={"first_name": "alice"},
            ),
        )
        self.assertEqual(
            "slug",
            get_next_unique_slug_value(
                CustomUser, "slug", "last_name", extra_filter_args={"first_name": "bob"}
            ),
        )
