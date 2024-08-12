# Block Resources

Block resources are files that are used to supplement a Block's main content. They are uploaded
by the course author and used either directly in the Block's html content. For example,
a .png image file can be a block resource to an HTML Block, while a video transcription .txt file
can be a resource for a VideoBlock.

## Block Resource Types

There are only three types of block resources at the moment:

- IMAGE (for a Block's HTML content)
- VIDEO_TRANSCRIPT (for a VideoBlock)
- GENERIC (for various uses, e.g. the "File Resource" block that provides a file download for a student.)

Block resource information is stored in the Resource model, and the file itself is stored in the Django media folder
via the model's `resource_file` property. The resource is linked into one or more Blocks where it is used via the
BlockResource join model...this allows one resource to be used in multiple Blocks across different courses. Each Resource
instance gets a unique uuid.

When possible, the author should try to re-use an existing Resource rather than
upload the same resource multiple times when authoring a course.

## Resources During Course Import

When importing a course, if the uuid of a resource contained in the imported course archive
already exists in the database, the existing Resource is used.

If the uuid does not exist, a new Resource is created, even if a resource with the same name
already exists in the media folder. (In the case the file name will be updated to be unique.)
