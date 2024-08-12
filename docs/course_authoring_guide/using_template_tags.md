# Using Template Tags

When using Composer to authoring a course, you can enter HTML text either in via the rich text editor (The WYSIWGY editor) or by writing raw HTML.

If you're comfortable writing raw HTML, KinesinLMS supports a small number of custom template tags in the HTML content
portions of the course. These tags are used to insert dynamic content into the course content.

These tags only work in "HTML Content" fields within certain blocks. (Some blocks have simple "text fields" which don't support HTML.)

!!! Note

    If you want to use these tags in a block, you must select the "Enable template tags" checkbox on the Block Settings tab when editing a block

Currently supported tags are listed below.

## Shortcut Hyperlinks

These tags make it easy to indicate a link to another part of the course without
having to write out a full, static link directly. Writing out the full link is a bit brittle as you'd
need to go back and change all your links if the course content changes. So using these shortcut
links is preferrable.

### Module Link

The `module_link` tag displays a link to a module, according to its module index.
It defaults to the first section and first unit in the module.

If you enter this HTML content as part of your raw html in Composer:

    ...more about this in {{ module_link 3 }}....

will generate HTML like:

    ...more about this in <a href="/course/1/module/some-module-slug/section/some-section-slug/unit/some-unit-slug">Module 3</a>....

### Section Link

The `module_link` tag displays a link to a section, according to its module and section index. It defaults to the first unit available in the section.

For example:

    {{ section_link 1 3 }}

### Unit Link

The `unit_link` tag displays a link to a section, according to its module and section index.

For example:

    {{ unit_link 1 3 2 }}

## Unit Link Slug

The `unit_slug_link` tag builds a link to a unit, given the CourseUnit's slug.
This is helpful if you don't know the exact module, section and unit index.

For example:

    {{ unit_slug_link 'my-course-unit-slug' }}

## Anon User ID

The `anon_user_id` tag writes the current user's anonymous ID into the HTML content.
This is useful when, for example, you need to create a link to an external service (like
Qualtrics) where the user's anonymous ID is required.

    {{ anon_user_id }}

## Username

The `username` tag writes the current user's username into the HTML content.

    {{ username }}
