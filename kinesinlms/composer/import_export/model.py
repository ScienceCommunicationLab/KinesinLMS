from dataclasses import dataclass


@dataclass()
class CourseImportOptions:
    create_forum_items: bool = True
