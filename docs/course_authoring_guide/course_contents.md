# Course Contents

When viewing a course in Composer, click the "Contents" tab to edit the actual course contents. This is where you'll do most
of your work, creating the units in a course and organizing them into a nested navigation.

## Course Navigation

A course is composed of a series of nested nodes: each course has one or more "module" nodes; each module node has
one or more "section" nodes; and each "section" node has one or more "unit" nodes. Mercifully, we stop there.

A "CourseUnit" object with the actual course content is then attached to each "unit" node.

Below is the course navigation for the Demo course.

![Screenshot of composer course nav](/docs/assets/authoring/modify_nodes.png)

So the first part of authoring a course could be building up your series of nested nodes to define the course
structure. You don't have to do it that way...you could build the nav gradually as you add course units.

Either way, you'll need to eventually define the all the nodes in your course navigation, and add content to each unit.

Use the drop-down buttons in the nav bar to add, edit or remove nodes.

![Screenshot of dropdown in composer nav](/docs/assets/authoring/node_dropdowns.png)

!!! note
    When you edit a node, we rely on the default Django admin panel for the user interface. It's a bit clunky. We hope to create UI directly
    in Composer for editing nodes.

## Course Unit Content

When editing a course, only one course unit is shown at a time. You can add, edit and remove the blocks that make up
the course unit.

![Screenshot of composer course unit edit page](/docs/assets/authoring/edit_unit_view.png)

### Blocks

Course contents are built up by adding one or more "Blocks" to a unit in your course.

A block is a piece of content that you create and configure. This is the current
set of block types available, although we hope to have more available soon:

  - **HTML Block** : Basic html content, primarly text and images. If you enter raw html you can use your own styles, script and so on.
  - **Video** : Holds a video link and displays a video player. At the moment only YouTube is supported, but other platforms (Wistia, etc.) will be added soon.
  - **File Resource** : A simple block to hold one or more file resources for the student to download.
  - **Forum Topic** : A block that connects to a forum topic in Discourse.
  - **Assessment** : An 'assessment' block, such as long-form text, multiple choice, etc.
  - **Survey** : A block that displays a survey from an external provider.
  - **Diagram** : Displays a 'simple interactive tool' for creating diagrams.
  - **TableTool** : Displays a 'simple interactive tool' for interactive tables.
  - **External Tool** : Displays an external tool connected by LTI (This one is still being developed)

More information about each block will be added to these docs soon. In the meantime, each block has integrated information on what information you'll need to enter.
