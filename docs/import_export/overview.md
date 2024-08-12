# Importing and Exporting

KinesinLMS supports a limited set of import and export features. Courses and be
exported and imported in a custom format and in the Common Cartridge format.

Export and import options are available in the Composer section of the site, under
the "Course" menu.

## Exporting

Courses can be exported to one of two formats:

### Exporting in KinesinLMS Format

This is a custom format used by KinesinLMS to export and import courses. It is a .zip file that
contains a json data file and one or more directories for course resources or other data.

### Common Cartridge

Common Cartridge is a standard format for exporting and importing courses. It is a .zip file that
contains a manifest file and one or more directories for course resources or other data.

KinesinLMS currently exports a small subset of the Common Cartridge 1.3 format.

## Importing

Courses can be imported from one of two formats:

- KinesinLMS Format
- SCL Format (Science Communication Labs format)

The import process will create a new course in the system and populate it with the content from the
imported file. The import process will not overwrite any existing courses or content.

### Importing KinesinLMS Format

This format should be a complete representation of a course exported from KinesinLMS. It is a .zip
that contains everything one would need to recreate the course in KinesinLMS.
