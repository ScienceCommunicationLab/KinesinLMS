"""
These are the classes for creating QTI assessments from our internal assessment models.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from kinesinlms.assessments.models import Assessment
from kinesinlms.learning_library.constants import AssessmentType

logger = logging.getLogger(__name__)


@dataclass
class QTIChoice:
    identifier: str
    text: str


@dataclass
class QTIAssessment:
    """
    Base class for holding the data we need to translate a KinesinLMS
    assessment to a QTI assessment for export in CC.
    """

    identifier: str
    title: str
    max_score: int
    question_text: str
    explanation: Optional[str] = None

    @abstractmethod
    def to_qti_xml(self) -> str:
        """Convert the assessment to QTI XML string"""
        pass


class MultipleChoiceQTIAssessment(QTIAssessment):
    """
    Class for holding the data we need to translate a KinesinLMS
    multiple choice assessment to a QTI multiple choice assessment
    for export in CC.
    """

    def __init__(
        self,
        identifier: str,
        title: str,
        max_score: int,
        question_text: str,
        choices: List[QTIChoice],
        correct_choice_keys: List[str],
        explanation: Optional[str] = None,
    ):
        super().__init__(identifier, title, max_score, question_text, explanation)
        self.choices = choices
        self.correct_choice_keys = correct_choice_keys

    def to_qti_xml(self) -> str:
        choices_xml = ""
        for choice in self.choices:
            choices_xml += f"""
                <response_label ident="{choice.identifier}">
                    <material>
                        <mattext texttype="text/plain">{choice.text}</mattext>
                    </material>
                </response_label>"""

        conditions_xml = ""
        for choice_key in self.correct_choice_keys:
            conditions_xml += f"""
            <respcondition continue="No">
                <conditionvar>
                    <varequal respident="response1">{choice_key}</varequal>
                </conditionvar>
                <setvar action="Set" varname="SCORE">{self.max_score}</setvar>
                <displayfeedback feedbacktype="Response" linkrefid="correct"/>
            </respcondition>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>multiple_choice_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{self.question_text}</mattext>
                    </material>
                    <response_lid ident="response1" rcardinality="Single">
                        <render_choice>
                            {choices_xml}
                        </render_choice>
                    </response_lid>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                    {conditions_xml}
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class TextEntryQTIAssessment(QTIAssessment):
    def to_qti_xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>text_entry_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{self.question_text}</mattext>
                    </material>
                    <response_str ident="response1" rcardinality="Single">
                        <render_fib>
                            <response_label ident="answer1"/>
                        </render_fib>
                    </response_str>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                    <respcondition>
                        <conditionvar>
                            <other/>
                        </conditionvar>
                        <setvar varname="SCORE" action="Set">0</setvar>
                    </respcondition>
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class DoneIndicatorQTIAssessment(QTIAssessment):
    """
    Class for representing a done/completion indicator as a QTI assessment.
    This represents a simple checkbox that students can check to indicate completion.
    The assessment just has a label (from definition_json.done_indicator_label) and
    a single checkbox that awards points when checked.
    """

    def to_qti_xml(self) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>true_false_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{self.question_text}</mattext>
                    </material>
                    <response_lid ident="response1" rcardinality="Single">
                        <render_choice>
                            <response_label ident="true">
                                <material>
                                    <mattext texttype="text/plain">Complete</mattext>
                                </material>
                            </response_label>
                        </render_choice>
                    </response_lid>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                    <respcondition continue="No">
                        <conditionvar>
                            <varequal respident="response1">true</varequal>
                        </conditionvar>
                        <setvar action="Set" varname="SCORE">{self.max_score}</setvar>
                        <displayfeedback feedbacktype="Response" linkrefid="correct"/>
                    </respcondition>
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class GenericQTIAssessment(QTIAssessment):
    """
    A fallback QTI assessment class that creates a text-only placeholder
    for assessment types that don't yet have specific QTI implementations.
    This prevents export failures while clearly indicating the limitation.
    """

    def to_qti_xml(self) -> str:
        message = f"This {self.title} assessment (type: {self.question_text}) cannot be exported to QTI format yet."

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">
    <assessment ident="{self.identifier}" title="{self.title}">
        <qtimetadata>
            <qtimetadatafield>
                <fieldlabel>qmd_assessmenttype</fieldlabel>
                <fieldentry>Assessment</fieldentry>
            </qtimetadatafield>
        </qtimetadata>
        <section ident="root_section">
            <item ident="{self.identifier}_item1" title="{self.title}">
                <itemmetadata>
                    <qtimetadata>
                        <qtimetadatafield>
                            <fieldlabel>question_type</fieldlabel>
                            <fieldentry>text_only_question</fieldentry>
                        </qtimetadatafield>
                        <qtimetadatafield>
                            <fieldlabel>points_possible</fieldlabel>
                            <fieldentry>{self.max_score}</fieldentry>
                        </qtimetadatafield>
                    </qtimetadata>
                </itemmetadata>
                <presentation>
                    <material>
                        <mattext texttype="text/html">{message}</mattext>
                    </material>
                </presentation>
                <resprocessing>
                    <outcomes>
                        <decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/>
                    </outcomes>
                </resprocessing>
            </item>
        </section>
    </assessment>
</questestinterop>"""


class QTIAssessmentFactory:
    """
    Factory for creating QTI assessment objects from our internal assessment models
    """

    def create_qti_assessment(self, assessment: Assessment) -> QTIAssessment:
        """
        Create appropriate QTI assessment based on assessment type

        Args:
            assessment: Assessment object

        Returns:
            QTIAssessment object
        """

        try:
            if assessment.type == AssessmentType.MULTIPLE_CHOICE.name:
                choices = []
                for choice in assessment.definition_json.get("choices", []):
                    choices.append(QTIChoice(identifier=choice["choice_key"], text=choice["text"]))

                correct_choices = assessment.solution_json.get("correct_choice_keys", [])

                return MultipleChoiceQTIAssessment(
                    identifier=assessment.id_for_cc,
                    title=assessment.label or "Untitled Assessment",
                    max_score=assessment.max_score,
                    question_text=assessment.question,
                    choices=choices,
                    correct_choice_keys=correct_choices,
                    explanation=assessment.explanation,
                )

            elif assessment.type == AssessmentType.LONG_FORM_TEXT.name:
                return TextEntryQTIAssessment(
                    identifier=str(assessment.id),
                    title=assessment.label or "Untitled Assessment",
                    max_score=assessment.max_score,
                    question_text=assessment.question,
                    explanation=assessment.explanation,
                )

            elif assessment.type == AssessmentType.DONE_INDICATOR.name:
                return DoneIndicatorQTIAssessment(
                    identifier=assessment.id_for_cc,
                    title=assessment.label or "Mark as Complete",
                    max_score=assessment.max_score,
                    question_text=assessment.definition_json.get("done_indicator_label", "Mark this item as complete"),
                    explanation=assessment.explanation,
                )

            else:
                # Instead of raising ValueError, return a generic assessment
                return GenericQTIAssessment(
                    identifier=assessment.id_for_cc,
                    title=assessment.label or "Untitled Assessment",
                    max_score=assessment.max_score,
                    question_text=assessment.type,  # Include the type in question text to make it clear what's missing
                    explanation=None,
                )
        except Exception as e:
            logger.error(f"Error creating QTI assessment for {assessment}: {str(e)}")
            # If anything goes wrong, fall back to generic assessment
            return GenericQTIAssessment(
                identifier=assessment.id_for_cc,
                title="Error Creating Assessment",
                max_score=0,
                question_text=f"Error creating QTI assessment of type {assessment.type}",
                explanation=None,
            )
