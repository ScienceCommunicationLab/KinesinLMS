from django.test import TestCase

from kinesinlms.course.serializers import IBiologyCoursesCourseSerializer


class TestIBiologyCoursesCourseSerializer(TestCase):

    @classmethod
    def setUpTestData(cls):
        pass

    def test_replace_keywords(self):
        """
        Test that old SCL-style keywords are replaced
        with new KinesinLMS template tags.
        """

        s = IBiologyCoursesCourseSerializer()

        input_html = """<p>Some html text with link ##MODULE_LINK[12]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% module_link 12 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##MODULE_LINK[ 12 ]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% module_link 12 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##MODULE_LINK[     12      ]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% module_link 12 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##SECTION_LINK[12,13]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% section_link 12 13 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##SECTION_LINK[12, 13]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% section_link 12 13 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##SECTION_LINK[    12,    13]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% section_link 12 13 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##UNIT_LINK[1,2,3]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% unit_link 1 2 3 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with link ##UNIT_LINK[1,    2,       3]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with link {% unit_link 1 2 3 %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with slug link ##UNIT_SLUG_LINK[slug]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with slug link {% unit_slug_link slug %} </p>"""
        self.assertEqual(expected_output_html, output_html)

        input_html = """<p>Some html text with slug link ##UNIT_SLUG_LINK[    some-slug     ]## </p>"""
        output_html = s._update_template_keywords(input_html)
        expected_output_html = """<p>Some html text with slug link {% unit_slug_link some-slug %} </p>"""
        self.assertEqual(expected_output_html, output_html)
